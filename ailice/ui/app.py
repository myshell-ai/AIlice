import time
import os
import re
import simplejson as json
import traceback
import queue
import librosa
import requests
import mimetypes
import threading
import appdirs
import logging
import traceback

from termcolor import colored
from flask import Flask, render_template, request, jsonify, Response, send_file
from werkzeug.utils import secure_filename
from logging.handlers import RotatingFileHandler

from ailice.common.AConfig import config
from ailice.core.AProcessor import AProcessor
from ailice.core.llm.ALLMPool import llmPool
from ailice.common.utils.ALogger import ALogger
from ailice.common.ARemoteAccessors import clientPool
from ailice.common.AMessenger import messenger
from ailice.AServices import StartServices, TerminateSubprocess

from ailice.common.APrompts import promptsManager
from ailice.prompts.APromptChat import APromptChat
from ailice.prompts.APromptMain import APromptMain
from ailice.prompts.APromptSearchEngine import APromptSearchEngine
from ailice.prompts.APromptResearcher import APromptResearcher
from ailice.prompts.APromptCoder import APromptCoder
from ailice.prompts.APromptModuleCoder import APromptModuleCoder
from ailice.prompts.APromptCoderProxy import APromptCoderProxy
from ailice.prompts.APromptArticleDigest import APromptArticleDigest



app = Flask(__name__)
processor = None
logger = None
speech = None
audioQue = None
sessionName = None
kwargs = None
lock = threading.Lock()

def Init(modelID: str, quantization: str, maxMemory: dict, prompt: str, temperature: float, flashAttention2: bool, speechOn: bool, ttsDevice: str, sttDevice: str, contextWindowRatio: float, chatHistoryPath: str):
    config.Initialize(modelID = modelID)
    config.chatHistoryPath = chatHistoryPath
    config.quantization = quantization
    config.maxMemory = maxMemory
    config.temperature = temperature
    config.flashAttention2 = flashAttention2
    config.speechOn = speechOn
    config.contextWindowRatio = contextWindowRatio

    print(colored("In order to simplify installation and usage, we have set local execution as the default behavior, which means AI has complete control over the local environment. \
To prevent irreversible losses due to potential AI errors, you may consider one of the following two methods: the first one, run AIlice in a virtual machine; the second one, install Docker, \
use the provided Dockerfile to build an image and container, and modify the relevant configurations in config.json. For detailed instructions, please refer to the documentation.", "red"))

    StartServices()
    for i in range(5):
        try:
            clientPool.Init()
            break
        except Exception as e:
            if i == 4:
                print(f"It seems that some peripheral module services failed to start. EXCEPTION: {str(e)}")
                traceback.print_tb(e.__traceback__)
                exit(-1)
            time.sleep(5)
            continue

    llmPool.Init([modelID])

    InitSpeech(speechOn, ttsDevice, sttDevice)
    
    InitServer()
    return

def InitSpeech(speechOn: bool, ttsDevice: str, sttDevice: str):
    global speech, audioQue
    
    if speechOn:
        import sounddevice as sd
        speech = clientPool.GetClient(config.services['speech']['addr'])
        print(colored(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>", "green"))
        print("The speech module is preparing speech recognition and TTS models, which may include the work of downloading weight data, so it may take a long time.")
        speech.PrepareModel()
        print("The speech module model preparation work is completed.")
        print(colored(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>", "green"))
        if any([re.fullmatch(r"(cuda|cpu)(:(\d+))?", s) == None for s in [ttsDevice, sttDevice]]):
            print("the value of ttsDevice and sttDevice should be a valid cuda device, such as cuda, cuda:0, or cpu, the default is cpu.")
            exit(-1)
        else:
            speech.SetDevices({"tts": ttsDevice, "stt": sttDevice})
    else:
        speech = None
        
    audioQue = queue.Queue(maxsize=100)

    def playAudio():
        while True:
            sd.play(*audioQue.get())
            sd.wait()
    if speechOn:
        threadPlayer = threading.Thread(target=playAudio, args=())
        threadPlayer.start()
    return

def LoadSession(sessionName: str, prompt: str, chatHistoryPath: str):
    global processor, logger
    
    sessionPath = os.path.join(config.chatHistoryPath, sessionName)
    
    os.makedirs(sessionPath, exist_ok=True)
    os.makedirs(os.path.join(sessionPath, "storage"), exist_ok=True)
    app.config['UPLOAD_FOLDER'] = f'{str(sessionPath)}/static/uploads'
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    print(colored(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>", "green"))
    print("We now start the vector database. Note that this may include downloading the model weights, so it may take some time.")
    storage = clientPool.GetClient(config.services['storage']['addr'])
    msg = storage.Open(os.path.join(sessionPath, "storage"))
    print(f"Vector database has been started. returned msg: {msg}")
    print(colored(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>", "green"))

    promptsManager.Init(storage=storage, collection=sessionName)
    for promptCls in [APromptChat, APromptMain, APromptSearchEngine, APromptResearcher, APromptCoder, APromptModuleCoder, APromptCoderProxy, APromptArticleDigest]:
        promptsManager.RegisterPrompt(promptCls)
    
    logger = ALogger(speech=None)
    processor = AProcessor(name="AIlice", modelID=kwargs['modelID'], promptName=prompt, outputCB=logger.Receiver, collection=sessionName)
    processor.RegisterModules([config.services['browser']['addr'],
                               config.services['arxiv']['addr'],
                               config.services['google']['addr'],
                               config.services['duckduckgo']['addr'],
                               config.services['scripter']['addr'],
                               config.services['computer']['addr']])
    
    p = os.path.join(sessionPath, "ailice_history.json")
    if os.path.exists(p):
        with open(p, "r") as f:
            processor.FromJson(json.load(f))
    return

def InitServer():
    os.makedirs(f'{config.chatHistoryPath}/logs', exist_ok=True)
    handler = RotatingFileHandler(f'{config.chatHistoryPath}/logs/app.log', maxBytes=10000, backupCount=1)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    return

def main():
    global kwargs
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--modelID',type=str,default='', help="modelID specifies the model. The currently supported models can be seen in llm/ALLMPool.py, just copy it directly. We will implement a simpler model specification method in the future.")
    parser.add_argument('--quantization',type=str,default='', help="quantization is the quantization option, you can choose 4bit or 8bit. The default is not quantized.")
    parser.add_argument('--maxMemory',type=dict,default=None, help='maxMemory is the memory video memory capacity constraint, the default is not set, the format when set is like "{0:"23GiB", 1:"24GiB", "cpu": "64GiB"}".')
    parser.add_argument('--prompt',type=str,default='main', help="prompt specifies the prompt to be executed, which is the type of agent. The default is 'main', this agent will decide to call the appropriate agent type according to your needs. You can also specify a special type of agent and interact with it directly.")
    parser.add_argument('--temperature',type=float,default=0.0, help="temperature sets the temperature parameter of LLM reasoning, the default is zero.")
    parser.add_argument('--flashAttention2',action='store_true', help="flashAttention2 is the switch to enable flash attention 2 to speed up inference. It may have a certain impact on output quality.")
    parser.add_argument('--contextWindowRatio',type=float,default=0.6, help="contextWindowRatio is a user-specified proportion coefficient, which determines the proportion of the upper limit of the prompt length constructed during inference to the LLM context window in some cases. The default value is 0.6.")
    parser.add_argument('--speechOn',action='store_true', help="speechOn is the switch to enable voice conversation. Please note that the voice dialogue is currently not smooth yet.")
    parser.add_argument('--ttsDevice',type=str,default='cpu',help='ttsDevice specifies the computing device used by the text-to-speech model. The default is "cpu", you can set it to "cuda" if there is enough video memory.')
    parser.add_argument('--sttDevice',type=str,default='cpu',help='sttDevice specifies the computing device used by the speech-to-text model. The default is "cpu", you can set it to "cuda" if there is enough video memory.')
    parser.add_argument('--chatHistoryPath',type=str,default=appdirs.user_data_dir("ailice", "Steven Lu"), help="chatHistoryPath is used to specify the chat history storage path.")
    #parser.add_argument('--share',type=bool,default=False, help="Whether to create a publicly shareable link for AIlice.")
    kwargs = vars(parser.parse_args())

    try:
        Init(**kwargs)
        app.run(debug=True, use_reloader=False)
    except Exception as e:
        print(f"Encountered an exception, AIlice is exiting: {str(e)}")
        traceback.print_tb(e.__traceback__)
        TerminateSubprocess()
        raise

def generate_response(message):
    try:
        with open(os.path.join(config.chatHistoryPath, sessionName, "ailice_history.json"), "w") as f:
            json.dump(processor.ToJson(), f, indent=2)
        
        threadLLM = threading.Thread(target=processor, args=(message,))
        threadLLM.start()
        while True:
            channel, txt, action = logger.queue.get()
            if ">" == channel:
                threadLLM.join()
                return
            ret = "\r\r" if "open"==action else ""
            ret += txt
            if config.speechOn:
                audioQue.put(speech.Text2Speech(txt))
            msg = json.dumps({'message': ret})
            yield f"data: {msg}\n\n"
    except Exception as e:
        app.logger.error(f"Error in generate_response: {e} {traceback.print_tb(e.__traceback__)}")
        yield f"data: Error occurred: {e}\n\n"

@app.route('/')
def index():
    with lock:
        return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    with lock:
        message = request.get_json().get('message', '')
        return Response(generate_response(message), mimetype='text/event-stream')

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    with lock:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        audio = request.files['audio']
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(audio.filename))
        audio.save(filepath)
        
        if config.speechOn:
            audio_data, sample_rate = librosa.load(filepath)
            message = speech.Speech2Text(audio_data, sample_rate)
        else:
            message = f"![audio]({str(filepath)})"
        return Response(generate_response(f"{message}"), mimetype='text/event-stream')

@app.route('/upload_image', methods=['POST'])
def upload_image():
    with lock:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        image = request.files['image']
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(image.filename))
        image.save(filepath)
        return Response(generate_response(f"![image]({str(filepath)})"), mimetype='text/event-stream')

@app.route('/new_chat')
def new_chat():
    global sessionName
    with lock:
        sessionName = "ailice_" + str(int(time.time()))
        LoadSession(sessionName=sessionName, prompt=kwargs['prompt'], chatHistoryPath=config.chatHistoryPath)
        return jsonify({"sessionName": sessionName})

@app.route('/load_history')
def load_history():
    global sessionName
    with lock:
        sessionName = request.args.get('name')
        LoadSession(sessionName=sessionName, prompt=kwargs['prompt'], chatHistoryPath=config.chatHistoryPath)
        historyPath = os.path.join(config.chatHistoryPath, sessionName, "ailice_history.json")
        if os.path.exists(historyPath):
            with open(historyPath, "r") as f:
                conversations = [(conv['role'], conv['msg']) for conv in json.load(f)['conversation']]
        else:
            conversations = []
        return jsonify(conversations)

@app.route('/list_histories')
def list_histories():
    with lock:
        histories = []
        for d in os.listdir(config.chatHistoryPath):
            p = os.path.join(config.chatHistoryPath, d, "ailice_history.json")
            if os.path.exists(p):
                with open(p, "r") as f:
                    content = json.load(f)
                    if len(content.get('conversation', [])) > 0:
                        histories.append((d, content.get('conversation')[0]['msg'][:10]))
        return jsonify(sorted(histories, key=lambda x: os.path.getmtime(os.path.join(config.chatHistoryPath, x[0], "ailice_history.json")), reverse = True))

@app.route('/interrupt', methods=['POST'])
def interrupt():
    messenger.Lock()
    return jsonify({'status': 'interrupted'})

@app.route('/sendmsg', methods=['POST'])
def sendmsg():
    msg = request.get_json().get('message', '')
    messenger.Put(msg)
    messenger.Unlock()
    return jsonify({'status': 'message sent', 'message': msg})

@app.route('/proxy', methods=['GET', 'HEAD'])
def proxy():
    href = request.args.get('href')
    if os.path.exists(href):
        if request.method == 'HEAD':
            mime_type, _ = mimetypes.guess_type(href)
            return send_file(href, mimetype=mime_type), 200
        return send_file(href)
    else:
        try:
            method = request.method
            if method == 'HEAD':
                resp = requests.head(href)
            else:
                resp = requests.get(href)
            
            resp.raise_for_status()
            
            response = Response(resp.content if method != 'HEAD' else None, content_type=resp.headers['Content-Type'])
            response.headers = {key: value for key, value in resp.headers.items()}
            return response
        except requests.exceptions.RequestException as e:
            return f'Error fetching the URL: {e}', 500
