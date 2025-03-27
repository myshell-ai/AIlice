import time
import os
import shutil
import sys
import re
import simplejson as json
import traceback
import librosa
import requests
import mimetypes
import threading
import tempfile
import logging
import traceback

from urllib.parse import unquote
from termcolor import colored
from flask import Flask, render_template, request, jsonify, Response, send_file, make_response
from werkzeug.utils import secure_filename
from logging.handlers import RotatingFileHandler

from ailice.common.AConfig import config
from ailice.core.AProcessor import AProcessor
from ailice.core.llm.ALLMPool import ALLMPool
from ailice.common.utils.ALogger import ALogger
from ailice.common.ARemoteAccessors import AClientPool
from ailice.common.AMessenger import AMessenger
from ailice.common.AGas import AGasTank
from ailice.AServices import StartServices, TerminateSubprocess

from ailice.common.APrompts import APromptsManager
from ailice.prompts.APromptChat import APromptChat
from ailice.prompts.APromptMain import APromptMain
from ailice.prompts.APromptSearchEngine import APromptSearchEngine
from ailice.prompts.APromptResearcher import APromptResearcher
from ailice.prompts.APromptCoder import APromptCoder
from ailice.prompts.APromptModuleCoder import APromptModuleCoder
from ailice.prompts.APromptCoderProxy import APromptCoderProxy
from ailice.prompts.APromptDocReader import APromptDocReader



app = Flask(__name__)
currentSession = None
context = dict()
speech = None
lock = threading.Lock()

def Init():
    print(colored("In order to simplify installation and usage, we have set local execution as the default behavior, which means AI has complete control over the local environment. \
To prevent irreversible losses due to potential AI errors, you may consider one of the following two methods: the first one, run AIlice in a virtual machine; the second one, install Docker, \
use the provided Dockerfile to build an image and container, and modify the relevant configurations in config.json. For detailed instructions, please refer to the documentation.", "red"))

    print(colored("If you find that ailice is running slowly or experiencing high CPU usage, please run `ailice_turbo` to install GPU acceleration support.", "green"))
    
    StartServices()
    
    InitServer()
    return

def InitSpeech(clientPool):
    global speech
    
    if config.speechOn:
        import sounddevice as sd
        speech = clientPool.GetClient(config.services['speech']['addr'])
        print(colored(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>", "green"))
        print("The speech module is preparing speech recognition and TTS models, which may include the work of downloading weight data, so it may take a long time.")
        speech.PrepareModel()
        print("The speech module model preparation work is completed.")
        print(colored(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>", "green"))
        if any([re.fullmatch(r"(cuda|cpu)(:(\d+))?", s) == None for s in [config.ttsDevice, config.sttDevice]]):
            print("the value of ttsDevice and sttDevice should be a valid cuda device, such as cuda, cuda:0, or cpu, the default is cpu.")
            exit(-1)
        else:
            speech.SetDevices({"tts": config.ttsDevice, "stt": config.sttDevice})
    else:
        speech = None
    return

def LoadSession(sessionName: str):
    global context, currentSession
    
    try:
        if sessionName in context:
            currentSession = sessionName
            return
        
        sessionPath = os.path.join(config.chatHistoryPath, sessionName)
        
        os.makedirs(sessionPath, exist_ok=True)
        os.makedirs(os.path.join(sessionPath, "storage"), exist_ok=True)
        app.config['UPLOAD_FOLDER'] = f'{str(sessionPath)}/uploads'
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        clientPool = AClientPool()
        for i in range(5):
            try:
                clientPool.Init()
                break
            except Exception as e:
                if i == 4:
                    print(f"It seems that some peripheral module services failed to start. EXCEPTION: {str(e)}")
                    print(e.tb) if hasattr(e, 'tb') else traceback.print_tb(e.__traceback__)
                time.sleep(5)
                continue
        
        InitSpeech(clientPool)
        
        print(colored(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>", "green"))
        print("We now start the vector database. Note that this may include downloading the model weights, so it may take some time.")
        storage = clientPool.GetClient(config.services['storage']['addr'])
        msg = storage.Open(os.path.join(sessionPath, "storage"))
        print(msg)
        print(colored(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>", "green"))

        llmPool = ALLMPool(config=config)
        llmPool.Init([config.modelID])

        promptsManager = APromptsManager()
        promptsManager.Init(storage=storage, collection=sessionName)
        promptsManager.RegisterPrompts([APromptChat, APromptMain, APromptSearchEngine, APromptResearcher, APromptCoder, APromptModuleCoder, APromptCoderProxy, APromptDocReader])

        messenger = AMessenger()

        logger = ALogger(speech=None)
        
        processor = AProcessor(name="AIlice", modelID=config.modelID, promptName=config.prompt, llmPool=llmPool, promptsManager=promptsManager, services=clientPool, messenger=messenger, outputCB=logger.Receiver, gasTank=AGasTank(1e8), config=config, collection=sessionName)
        moduleList = [serviceCfg['addr'] for serviceName, serviceCfg in config.services.items()]
        if not config.speechOn:
            moduleList.remove(config.services['speech']['addr'])
        processor.RegisterModules(moduleList)
        
        p = os.path.join(sessionPath, "ailice_history.json")
        if os.path.exists(p):
            with open(p, "r") as f:
                processor.FromJson(json.load(f))
        context[sessionName] = {'processor': processor, 'llmPool': llmPool, 'messenger': messenger, 'logger': logger}
        currentSession = sessionName
    except Exception as e:
        print('Exception: ', str(e))
        print(e.tb) if hasattr(e, 'tb') else traceback.print_tb(e.__traceback__)
        exit(-1)
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
    config.Initialize()
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--modelID',type=str,default=config.modelID, help="modelID specifies the model. There are two modes for model configuration. In the first mode, the model is uniformly specified by modelID. In the second mode, different types of agents will run on different models. When this parameter is an empty string (unspecified), the second mode will be used automatically, i.e., the models configured individually for different agents under the agentModelConfig field in config.json will be used. The currently supported models can be seen in config.json. Default: %(default)s")
    parser.add_argument('--quantization',type=str,default=config.quantization, help="quantization is the quantization option, you can choose 4bit or 8bit. Default: %(default)s")
    parser.add_argument('--maxMemory',type=dict,default=config.maxMemory, help='maxMemory is the memory video memory capacity constraint, the format when set is like "{0:"23GiB", 1:"24GiB", "cpu": "64GiB"}". Default: %(default)s')
    parser.add_argument('--prompt',type=str,default=config.prompt, help="prompt specifies the prompt to be executed, which is the type of agent. Default: %(default)s")
    parser.add_argument('--temperature',type=float,default=config.temperature, help="temperature sets the temperature parameter of LLM reasoning. Default: %(default)s")
    parser.add_argument('--flashAttention2',type=bool,default=config.flashAttention2, help="flashAttention2 is the switch to enable flash attention 2 to speed up inference. It may have a certain impact on output quality. Default: %(default)s")
    parser.add_argument('--contextWindowRatio',type=float,default=config.contextWindowRatio, help="contextWindowRatio is a user-specified proportion coefficient, which determines the proportion of the upper limit of the prompt length constructed during inference to the LLM context window in some cases. Default: %(default)s")
    parser.add_argument('--speechOn',type=bool,default=config.speechOn, help="speechOn is the switch to enable voice conversation. Please note that the voice dialogue is currently not smooth yet. Default: %(default)s")
    parser.add_argument('--ttsDevice',type=str,default=config.ttsDevice,help='ttsDevice specifies the computing device used by the text-to-speech model. You can set it to "cuda" if there is enough video memory. Default: %(default)s')
    parser.add_argument('--sttDevice',type=str,default=config.sttDevice,help='sttDevice specifies the computing device used by the speech-to-text model. You can set it to "cuda" if there is enough video memory. Default: %(default)s')
    parser.add_argument('--resetApiKey',action='store_true', help="Whether to reset the model's API key after startup.")
    parser.add_argument('--chatHistoryPath',type=str,default=config.chatHistoryPath, help="chatHistoryPath is used to specify the chat history storage path. Default: %(default)s")
    parser.add_argument('--certificate',type=str,default=config.certificate, help="""Certificate settings for the web interface. The simplest option is an empty string, which will use the HTTP protocol for the UI web page. Setting it to 'adhoc' will use a self-generated certificate, providing encryption for the data flow between the UI and server, but it requires dismissing browser security warnings. The most secure method is to apply for a certificate and set this parameter to '{"cert": "your_cert.pem", "key": "your_key.pem")'. Default: %(default)s""")
    parser.add_argument('--expose',type=bool,default=False, help="Whether to provide public access. Default: %(default)s")
    #parser.add_argument('--share',type=bool,default=False, help="Whether to create a publicly shareable link for AIlice.")
    kwargs = vars(parser.parse_args())

    config.Check4Update(kwargs['modelID'], kwargs['resetApiKey'])
    config.Update(kwargs)

    try:
        Init()
        if kwargs['certificate'] == '':
            ssl_context = None
        elif kwargs['certificate'] == 'adhoc':
            ssl_context = 'adhoc'
        else:
            try:
                certCfg = json.loads(kwargs['certificate'])
                ssl_context = (certCfg['cert'], certCfg['key'])
            except Exception as e:
                print("""The certificate configuration you entered could not be recognized. Please set it according to the following format: {"cert": "your_cert.pem", "key": "your_key.pem")""")
                sys.exit(0)
        
        app.run(debug=False, ssl_context=ssl_context, host='0.0.0.0' if kwargs['expose'] else '127.0.0.1', port=5000)
        
    except Exception as e:
        print(f"Encountered an exception, AIlice is exiting: {str(e)}")
        print(e.tb) if hasattr(e, 'tb') else traceback.print_tb(e.__traceback__)
        TerminateSubprocess()
        raise

def generate_response(message):
    try:
        context[currentSession]['processor'].SetGas(amount=1e8)
        threadLLM = threading.Thread(target=context[currentSession]['processor'], args=(message,))
        threadLLM.start()
        depth = -1
        braketMap = {"<": 1, ">": -1}
        
        while True:
            channel, txt, action = context[currentSession]['logger'].queue.get()
            
            depth += braketMap.get(channel, 0)
            if (-1 == depth) and (">" == channel):
                threadLLM.join()
                with open(os.path.join(config.chatHistoryPath, currentSession, "ailice_history.json"), "w") as f:
                    json.dump(context[currentSession]['processor'].ToJson(), f, indent=2)
                return
            elif (channel in ["<", ">"]):
                continue
            
            msg = json.dumps({'message': txt, 'role': channel, 'action': action, 'msgType': 'internal' if (depth > 0) else 'user-ailice'})
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
    with lock:
        sessionName = "ailice_" + str(int(time.time()))
        LoadSession(sessionName=sessionName)
        return jsonify({"sessionName": sessionName})

@app.route('/load_history')
def load_history():
    with lock:
        sessionName = request.args.get('name')
        needLoading = (sessionName != currentSession)
        if needLoading:
            LoadSession(sessionName=sessionName)
        historyPath = os.path.join(config.chatHistoryPath, sessionName, "ailice_history.json")
        if os.path.exists(historyPath):
            with open(historyPath, "r") as f:
                data = json.load(f)
                conversations = [(f"{conv['role']}_{data['name']}", conv['msg']) for conv in data['conversation']]
        else:
            conversations = []
        return jsonify(conversations)

@app.route('/delete_history/<string:sessionName>', methods=['DELETE'])
def delete_history(sessionName):
    with lock:
        historyDir = os.path.join(config.chatHistoryPath, sessionName)
        if os.path.exists(historyDir):
            shutil.rmtree(historyDir)
            return '', 204
        else:
            return jsonify({'error': 'History item not found'}), 404

@app.route('/list_histories')
def list_histories():
    with lock:
        histories = []
        for d in os.listdir(config.chatHistoryPath):
            p = os.path.join(config.chatHistoryPath, d, "ailice_history.json")
            if os.path.exists(p):
                with open(p, "r") as f:
                    try:
                        content = json.load(f)
                    except Exception as e:
                        continue
                    if len(content.get('conversation', [])) > 0:
                        histories.append((d, content.get('conversation')[0]['msg']))
        return jsonify(sorted(histories, key=lambda x: os.path.getmtime(os.path.join(config.chatHistoryPath, x[0], "ailice_history.json")), reverse = True))

@app.route('/interrupt', methods=['POST'])
def interrupt():
    global context
    context[currentSession]['messenger'].Lock()
    return jsonify({'status': 'interrupted'})

@app.route('/sendmsg', methods=['POST'])
def sendmsg():
    global context
    msg = request.get_json().get('message', '')
    context[currentSession]['messenger'].Put(msg)
    context[currentSession]['messenger'].Unlock()
    return jsonify({'status': 'message sent', 'message': msg})

@app.route('/proxy', methods=['GET', 'HEAD'])
def proxy():
    href = unquote(request.args.get('href'))
    var = context[currentSession]['processor'].interpreter.env.get(href, None)
    if var and (type(var).__name__ in ['AImage', 'AVideo']):
        with tempfile.NamedTemporaryFile(mode='bw', delete=True) as temp:
            temp.write(var.data)
            temp.flush()
            if request.method == 'HEAD':
                response = make_response("")
                response.headers["Content-Type"] = {"AImage": "image/jpeg", "AVideo": "video/mp4"}[type(var).__name__]
            else:
                response = send_file(os.path.abspath(temp.name))
    else:
        computer = context[currentSession]["processor"].services.GetClient(config.services['computer']['addr'])
        try:
            r = computer.Proxy(href, request.method)
            responseInfo = next(r)
            def gen():
                yield from r

            contentType = responseInfo['headers'].get('Content-Type', '')
            response = Response(gen(), status=responseInfo['status_code'], content_type=contentType)
            
            for key, value in responseInfo['headers'].items():
                if key.lower() not in ('content-encoding', 'content-length', 'transfer-encoding', 'connection'):
                    response.headers[key] = value

            if contentType.lower() in ('image/svg+xml', 'application/svg+xml'):
                response.headers['Content-Type'] = 'image/svg+xml'
                response.headers['Content-Disposition'] = 'inline'
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = '*'
        except requests.exceptions.RequestException as e:
            return f'Error fetching the URL: {e}', 500
    
    isLocalFile = os.path.exists(href) if href.startswith('/') or href.startswith('file://') or (':/' in href) else False
    if isLocalFile:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    else:
        response.headers['Cache-Control'] = 'public, max-age=60'
    return response