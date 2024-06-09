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
import logging

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
app.config['UPLOAD_FOLDER'] = './static/uploads'
LOG_FILE = './logs/app.log'

processor = None
sessionDir = None
logger = None
speech = None
audioQue = None

def mainLoop(modelID: str, quantization: str, maxMemory: dict, prompt: str, temperature: float, flashAttention2: bool, speechOn: bool, ttsDevice: str, sttDevice: str, contextWindowRatio: float, session: str):
    global processor, sessionDir, logger, speech, audioQue
    
    config.Initialize(modelID = modelID)
    config.quantization = quantization
    config.maxMemory = maxMemory
    config.temperature = temperature
    config.flashAttention2 = flashAttention2
    config.speechOn = speechOn
    config.contextWindowRatio = contextWindowRatio

    sessionDir = session
    
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

    print(colored(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>", "green"))
    print("We now start the vector database. Note that this may include downloading the model weights, so it may take some time.")
    storage = clientPool.GetClient(config.services['storage']['addr'])
    msg = storage.Open("")
    print(f"Vector database has been started. returned msg: {msg}")
    print(colored(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>", "green"))
    
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
    
    timestamp = str(int(time.time()))
    collection = "ailice_" + timestamp

    promptsManager.Init(storage=storage, collection=collection)
    for promptCls in [APromptChat, APromptMain, APromptSearchEngine, APromptResearcher, APromptCoder, APromptModuleCoder, APromptCoderProxy, APromptArticleDigest]:
        promptsManager.RegisterPrompt(promptCls)
    
    llmPool.Init([modelID])
    
    logger = ALogger(speech=None)
    processor = AProcessor(name="AIlice", modelID=modelID, promptName=prompt, outputCB=logger.Receiver, collection=collection)
    processor.RegisterModules([config.services['browser']['addr'],
                               config.services['arxiv']['addr'],
                               config.services['google']['addr'],
                               config.services['duckduckgo']['addr'],
                               config.services['scripter']['addr'],
                               config.services['computer']['addr']])
    
    if "" != session.strip():
        os.makedirs(session, exist_ok=True)
    if os.path.exists(os.path.join(session, "ailice_history.json")):
        with open(os.path.join(session, "ailice_history.json"), "r") as f:
            processor.FromJson(json.load(f))
        
    audioQue = queue.Queue(maxsize=100)

    def playAudio():
        while True:
            sd.play(*audioQue.get())
            sd.wait()
    if speechOn:
        threadPlayer = threading.Thread(target=playAudio, args=())
        threadPlayer.start()
    return

def main():
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
    parser.add_argument('--session',type=str,default='', help="session is used to specify the session storage path, if the directory is not empty, the conversation history stored in that directory will be loaded and updated.")
    #parser.add_argument('--share',type=bool,default=False, help="Whether to create a publicly shareable link for AIlice.")
    kwargs = vars(parser.parse_args())

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    if not os.path.exists('./logs'):
        os.makedirs('./logs')
    handler = RotatingFileHandler(LOG_FILE, maxBytes=10000, backupCount=1)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)

    try:
        mainLoop(**kwargs)
        app.run(debug=True, use_reloader=False)
    except Exception as e:
        print(f"Encountered an exception, AIlice is exiting: {str(e)}")
        traceback.print_tb(e.__traceback__)
        TerminateSubprocess()
        raise

def generate_response(message):
    try:
        if "" != sessionDir.strip():
            with open(os.path.join(sessionDir, "ailice_history.json"), "w") as f:
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
        app.logger.error(f"Error in generate_response: {e}")
        yield f"data: Error occurred: {e}\n\n"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    message = request.get_json().get('message', '')
    return Response(generate_response(message), mimetype='text/event-stream')

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
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
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    image = request.files['image']
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(image.filename))
    image.save(filepath)
    return Response(generate_response(f"![image]({str(filepath)})"), mimetype='text/event-stream')

@app.route('/load_history')
def load_history_route():
    return jsonify([])

@app.route('/list_histories')
def list_histories_route():
    return jsonify([])

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
