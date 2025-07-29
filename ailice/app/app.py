import os
import sys
import simplejson as json
import traceback
import requests
import appdirs
import tempfile
import traceback
import logging

from functools import wraps
from logging.handlers import RotatingFileHandler
from urllib.parse import unquote
from flask import render_template, request, jsonify, Response, send_file, redirect, url_for, session, make_response

from ailice.common.AConfig import config
from ailice.AServices import StartServices, TerminateSubprocess

from ailice.app.factory import CreateApp
from ailice.app.context import UserContext
from ailice.app.log import logger
from ailice.app.exceptions import AWExceptionSessionNotExist

from datetime import datetime, timedelta

AILICE_CONFIG = os.path.join(appdirs.user_config_dir("ailice", "Steven Lu"), "config.json")

app = CreateApp()
context = UserContext(userID="0")

def Init():
    StartServices()
    logger.info("Services started")
    
    context.Create()

    InitServer()
    return

def InitServer():
    os.makedirs(f'{config.chatHistoryPath}/logs', exist_ok=True)
    handler = RotatingFileHandler(f'{config.chatHistoryPath}/logs/app.log', maxBytes=1000000, backupCount=5)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    logger.info(f"Flask app logger configured to write to {config.chatHistoryPath}/logs/app.log")
    return

def main():
    config.Initialize(configFile=AILICE_CONFIG)
    logger.info("Configuration initialized")
    
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
    parser.add_argument('--logLevel',type=str,default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default: %(default)s")
    #parser.add_argument('--share',type=bool,default=False, help="Whether to create a publicly shareable link for AIlice.")
    kwargs = vars(parser.parse_args())

    # Set log level based on command line argument
    log_level = getattr(logging, kwargs['logLevel'].upper(), logging.INFO)
    logger.setLevel(log_level)
    logger.info(f"Log level set to {kwargs['logLevel']}")

    config.Check4Update(kwargs['modelID'], kwargs['resetApiKey'])
    config.Update(kwargs)
    logger.info(f"Configuration updated with command line arguments")

    try:
        Init()
        if kwargs['certificate'] == '':
            ssl_context = None
            logger.info("Starting server with HTTP (no SSL)")
        elif kwargs['certificate'] == 'adhoc':
            ssl_context = 'adhoc'
            logger.info("Starting server with self-signed certificate")
        else:
            try:
                certCfg = json.loads(kwargs['certificate'])
                ssl_context = (certCfg['cert'], certCfg['key'])
                logger.info(f"Starting server with certificate: {certCfg['cert']} and key: {certCfg['key']}")
            except Exception as e:
                error_msg = """The certificate configuration you entered could not be recognized. Please set it according to the following format: {"cert": "your_cert.pem", "key": "your_key.pem")"""
                logger.error(f"{error_msg}. Error: {str(e)}")
                print(error_msg)
                sys.exit(0)
        
        host = '0.0.0.0' if kwargs['expose'] else '127.0.0.1'
        port = 5000
        logger.info(f"Starting Flask server on {host}:{port}")
        app.run(debug=False, ssl_context=ssl_context, host=host, port=port)
        
    except Exception as e:
        error_msg = f"Encountered an exception, AIlice is exiting: {str(e)}"
        logger.critical(error_msg, exc_info=True)
        print(error_msg)
        if hasattr(e, 'tb'):
            print(e.tb)
        else:
            traceback.print_tb(e.__traceback__)
        TerminateSubprocess()
        raise

@app.route('/get_announcement', methods=['GET'])
def get_announcement():
    logger.debug("Announcement requested")
    return jsonify({'announcement': ""})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/list_agent_type', methods=['GET'])
def list_agent_type():
    logger.debug("Agent type list requested")
    return jsonify(["main", "researcher", "search-engine", "coder-proxy", "coder", "doc-reader", "module-coder", "chat"])

@app.route('/current_session', methods=['GET'])
def current_session():
    logger.debug("Current session requested")
    try:
        return jsonify(context.CurrentSession().Description())
    except AWExceptionSessionNotExist as e:
        return jsonify({})

@app.route('/stream', methods=['GET'])
def stream():
    logger.info(f"Message stream acquired")
    try:
        return Response(
            context.CurrentSession().MsgStream(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*'
            }
        )
    except AWExceptionSessionNotExist as e:
        return jsonify({"error": "Session not found"}), 404

@app.route('/message', methods=['POST'])
def message():
    message = request.form.get('message', '')
    
    if 'files_for_perception[]' in request.files:
        message = f"{message}\n\n<!-- The following audio/video/image files are marked with extended markdown syntax for your analysis -->"
        files_for_perception = request.files.getlist('files_for_perception[]')
        for file in files_for_perception:
            if file and file.filename:
                file_path = context.CurrentSession().UploadFile(file.filename, file.read(), file.content_type)
                message = f"{message}\n\n![{file_path}]({file_path})"
    
    if 'files_for_processing[]' in request.files:
        message = f"{message}\n\n<!-- Here are other attached files. To make the agent actually read the file content (not just see the path), mark it with extended markdown syntax. Check file size first to avoid consuming too many tokens on large files. -->\n\nAttached files:"
        files_for_processing = request.files.getlist('files_for_processing[]')
        for file in files_for_processing:
            if file and file.filename:
                file_path = context.CurrentSession().UploadFile(file.filename, file.read(), file.content_type)
                message = f"{message}\n\ntype: {file.content_type}   length: {file.content_length}   path: {file_path}"
    
    logger.info(f"Chat message received")
    logger.debug(f"Message content: {message[:50]}{'...' if len(message) > 50 else ''}\nfiles_for_perception: {len(files_for_perception) if 'files_for_perception' in locals() else 0}\nfiles_for_processing: {len(files_for_processing) if 'files_for_processing' in locals() else 0}")
    context.CurrentSession().Message(message)
    return "", 204

@app.route('/new_chat')
def new_chat():
    session_name = context.NewSession()
    logger.info(f"New chat session '{session_name}' created")
    return jsonify(context.CurrentSession().Description())

@app.route('/load_history')
def load_history():
    session_name = request.args.get('name')
    logger.info(f"Loading chat history '{session_name}'")
    context.LoadSession(session_name)
    return jsonify(context.CurrentSession().Description())

@app.route('/get_history')
def get_history():
    session_name = request.args.get('name')
    logger.info(f"Getting chat history '{session_name}'")
    return jsonify(context.GetSession(session_name))

@app.route('/delete_history/<string:sessionName>', methods=['DELETE'])
def delete_history(sessionName):
    if context.DeleteSession(sessionName):
        logger.info(f"Chat history '{sessionName}' deleted")
        return '', 204
    else:
        logger.warning(f"Failed to delete chat history '{sessionName}': History not found")
        return jsonify({'error': 'History item not found'}), 404

@app.route('/list_histories')
def list_histories():
    logger.debug(f"Listing chat histories")
    return jsonify(context.ListSessions())

@app.route('/interrupt', methods=['POST'])
def interrupt():
    context.CurrentSession().Interrupt()
    logger.info(f"Chat interrupted by user")
    return jsonify({'status': 'interrupted'})

@app.route('/sendmsg', methods=['POST'])
def sendmsg():
    message = request.form.get('message', '')
    
    if 'files_for_perception[]' in request.files:
        message = f"{message}\n\n<!-- The following audio/video/image files are marked with extended markdown syntax for your analysis -->"
        files_for_perception = request.files.getlist('files_for_perception[]')
        for file in files_for_perception:
            if file and file.filename:
                file_path = context.CurrentSession().UploadFile(file.filename, file.read(), file.content_type)
                message = f"{message}\n\n![{file_path}]({file_path})"
    
    if 'files_for_processing[]' in request.files:
        message = f"{message}\n\n<!-- Here are other attached files. To make the agent actually read the file content (not just see the path), mark it with extended markdown syntax. Check file size first to avoid consuming too many tokens on large files. -->\n\nAttached files:"
        files_for_processing = request.files.getlist('files_for_processing[]')
        for file in files_for_processing:
            if file and file.filename:
                file_path = context.CurrentSession().UploadFile(file.filename, file.read(), file.content_type)
                message = f"{message}\n\ntype: {file.content_type}   length: {file.content_length}   path: {file_path}"
    
    context.CurrentSession().SendMsg(message)

    logger.info(f"Message sent")
    logger.debug(f"Message content: {message[:50]}{'...' if len(message) > 50 else ''}\nfiles_for_perception: {len(files_for_perception) if 'files_for_perception' in locals() else 0}\nfiles_for_processing: {len(files_for_processing) if 'files_for_processing' in locals() else 0}")
    return jsonify({'status': 'message sent', 'message': message})

@app.route('/get_settings', methods=['POST'])
def get_settings():
    patches = request.get_json().get('patches')
    logger.debug(f"Settings requested")
    return jsonify({"schema": context.Setup(patches, apply = False)})

@app.route('/update_settings', methods=['POST'])
def update_settings():
    patches = request.get_json().get('patches')
    logger.info(f"Settings updated")
    return jsonify({"schema": context.Setup(patches, apply = True)})

@app.route('/proxy', methods=['GET', 'HEAD'])
def proxy():
    href = unquote(request.args.get('href'))
    logger.debug(f"Proxy request for {href}")
    res = context.CurrentSession().Proxy(href, request.method)

    meta = next(res)
    if "variable" == meta["type"]:
        with tempfile.NamedTemporaryFile(mode='bw', delete=True) as temp:
            temp.write(meta["data"].data)
            temp.flush()
            if request.method == 'HEAD':
                response = make_response("")
                response.headers["Content-Type"] = {"AImage": "image/jpeg", "AVideo": "video/mp4"}[type(meta["data"]).__name__]
            else:
                response = send_file(os.path.abspath(temp.name))
    else:
        try:
            responseInfo = meta["responseInfo"]
            def gen():
                yield from res

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
            error_msg = f'Error fetching the URL: {e}'
            logger.error(error_msg)
            return error_msg, 500
    
    isLocalFile = os.path.exists(href) if href.startswith('/') or href.startswith('file://') or (':/' in href) else False
    if isLocalFile:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    else:
        response.headers['Cache-Control'] = 'public, max-age=60'
    return response

if __name__ == "__main__":
    main()