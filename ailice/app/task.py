import os
import re
import time
import json
import threading
import librosa
import traceback
import typing
import ctypes
from werkzeug.utils import secure_filename
from transitions.extensions import LockedMachine

from ailice.core.AProcessor import AProcessor
from ailice.core.llm.ALLMPool import ALLMPool
from ailice.common.AConfig import AConfig
from ailice.common.ARemoteAccessors import AClientPool
from ailice.common.AMessenger import AMessenger
from ailice.common.AGas import AGasTank

from ailice.common.APrompts import APromptsManager
from ailice.prompts.APromptChat import APromptChat
from ailice.prompts.APromptMain import APromptMain
from ailice.prompts.APromptSearchEngine import APromptSearchEngine
from ailice.prompts.APromptResearcher import APromptResearcher
from ailice.prompts.APromptCoder import APromptCoder
from ailice.prompts.APromptModuleCoder import APromptModuleCoder
from ailice.prompts.APromptCoderProxy import APromptCoderProxy
from ailice.prompts.APromptDocReader import APromptDocReader

from ailice.app.decorators import atomic_transition
from ailice.app.log import logger
from ailice.app.msgque import KMsgQue, Empty
from ailice.app.exceptions import *


def GetThreadID(thread):
    if not thread.is_alive():
        raise threading.ThreadError("The thread is not active")
    for tid, tobj in threading._active.items():
        if tobj is thread:
            return tid
    raise AssertionError("Could not find thread ID")

def StopThread(thread):
    try:
        thread_id = GetThreadID(thread)
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_long(thread_id),
            ctypes.py_object(SystemExit)
        )
        if res == 0:
            logger.error(f"Invalid thread ID")
        elif res > 1:
            logger.critical(f"PyThreadState_SetAsyncExc FAILED.")
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), None)
    except Exception as e:
        pass
    return

def ExtractMessages(history: dict, depth: int) -> list:
    if history is None:
        return []
    messages = [{'message': r['msg'], 'role': f"{r['role']}_{history['name']}", 'action': '', 'msgType': 'internal' if (depth > 0) else 'user-ailice', 'time': r['time']} for r in history["conversation"]]
    for _, p in history['subProcessors'].items():
        messages += ExtractMessages(p, depth+1)
    return sorted(messages, key=lambda x: x['time'])

class TaskSession():
    states = ["init", "ready", "generating", "interrupted", "stopping"]

    def __init__(self, sessionName, sessionPath, clientSecretFile, serverPublicFile):
        self.sessionName = sessionName
        self.title = None
        self.sessionPath = sessionPath
        self.clientSecretFile = str(clientSecretFile)
        self.serverPublicFile = str(serverPublicFile)
        self.config = None

        self.threadLLM = None
        self.clientPool = None
        self.processor = None
        self.llmPool = None
        self.messenger = None
        self.alogger = None
        self.stopFlag = False
        self.streamNum = 0
        
        self.machine = LockedMachine(model=self, states=TaskSession.states, initial='init')
        self.machine.add_transition(trigger='create', source='init', dest='ready')
        self.machine.add_transition(trigger='stop', source='*', dest='stopping')
        self.machine.add_transition(trigger='release', source='stopping', dest='init')
        self.machine.add_transition(trigger='upload', source=['ready', 'interrupted'], dest='=')
        self.machine.add_transition(trigger='input', source='ready', dest='generating')
        self.machine.add_transition(trigger='interrupt', source=['generating', 'interrupted'], dest='interrupted')
        self.machine.add_transition(trigger='sendmsg', source='interrupted', dest='generating')
        self.machine.add_transition(trigger='answered', source='generating', dest='ready')
        self.machine.add_transition(trigger='dump', source=['ready', 'stopping'], dest='=')
        self.machine.add_transition(trigger='desc', source='*', dest='=')
        self.machine.add_transition(trigger='stream', source='*', dest='=')
        self.methodLock = threading.RLock()
        logger.debug(f"TaskSession initialized: {sessionName}")
        return
    
    @atomic_transition("dump")
    def Save(self):
        if (self.sessionPath is not None) and (self.processor is not None):
            try:
                history_path = os.path.join(self.sessionPath, "ailice_history.json")
                with open(history_path, "w") as f:
                    json.dump(self.processor.ToJson(), f, indent=2)
                logger.info(f"Saved history to {history_path}")
            except Exception as e:
                logger.error(f"TaskSession::Save() Exception: Dump history FAILED. {str(e)}", exc_info=True)
        return
    
    @atomic_transition("create")
    def Create(self, config):
        sessionName, sessionPath = self.sessionName, self.sessionPath
        self.config = config
        
        logger.info(f"Creating session {sessionName} at {sessionPath}")
        os.makedirs(sessionPath, exist_ok=True)
        os.makedirs(os.path.join(sessionPath, "storage"), exist_ok=True)
        os.makedirs(os.path.join(sessionPath, "uploads"), exist_ok=True)

        history = None
        p = os.path.join(sessionPath, "ailice_history.json")
        if os.path.exists(p):
            with open(p, "r") as f:
                if os.path.getsize(p) > 0:
                    history = json.load(f)
                    logger.info(f"Loaded history from {p}")
                else:
                    logger.info(f"Empty history file: {p}")
        
        self.CreateAilice(history=history)
        logger.info(f"Session {sessionName} created successfully")
        return

    def CreateAilice(self, history: typing.Optional[dict]=None):
        sessionName, sessionPath = self.sessionName, self.sessionPath

        self.clientPool = AClientPool()
        for i in range(5):
            try:
                self.clientPool.Init()
                logger.info("Client pool initialized successfully")
                break
            except Exception as e:
                if i == 4:
                    error_msg = f"It seems that some peripheral module services failed to start. EXCEPTION: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    if hasattr(e, 'tb'):
                        logger.error(e.tb)
                    else:
                        logger.error(traceback.format_exc())
                time.sleep(5)
                continue
        
        self.InitSpeech(self.clientPool)
        
        logger.info("Starting vector database. This may include downloading model weights.")
        storage = self.clientPool.GetClient(self.config.services['storage']['addr'])
        with storage.Timeout(-1):
            msg = storage.Open(os.path.join(sessionPath, "storage"))
        logger.info(f"Storage response: {msg}")

        llmPool = ALLMPool(config=self.config)
        llmPool.Init([self.config.modelID])
        logger.info(f"LLM Pool initialized with model: {self.config.modelID}")

        promptsManager = APromptsManager()
        promptsManager.Init(storage=storage, collection=sessionName)
        promptsManager.RegisterPrompts([APromptChat, APromptMain, APromptSearchEngine, APromptResearcher, APromptCoder, APromptModuleCoder, APromptCoderProxy, APromptDocReader])
        logger.info("Prompts manager initialized and prompts registered")

        messenger = AMessenger()

        alogger = KMsgQue()
        alogger.Load(ExtractMessages(history, 0))
        
        processor = AProcessor(name="AIlice", modelID=self.config.modelID, promptName=self.config.prompt, llmPool=llmPool, promptsManager=promptsManager, services=self.clientPool, messenger=messenger, outputCB=alogger.Receiver, gasTank=AGasTank(1e8), config=self.config, collection=sessionName)
        moduleList = [self.config.services['arxiv']['addr'],
                      self.config.services['google']['addr'],
                      self.config.services['duckduckgo']['addr'],
                      self.config.services['browser']['addr'],
                      self.config.services['scripter']['addr'],
                      self.config.services['computer']['addr']]
        
        if self.config.speechOn:
            moduleList.append(self.config.services['speech']['addr'])
        processor.RegisterModules(moduleList)
        logger.info(f"Processor initialized with {len(moduleList)} modules")
        
        if history is not None:
            processor.FromJson(history)
            self.title = history["conversation"][0]["msg"] if len(history["conversation"]) > 0 else "New Chat"
            logger.info(f"History Loaded.")

        self.processor = processor
        self.llmPool = llmPool
        self.messenger = messenger
        self.alogger = alogger
        logger.info(f"Session {sessionName} created successfully")
        return

    @atomic_transition("stop")
    def Stop(self):
        try:
            logger.info(f"Stopping session {self.sessionName}")
            self.stopFlag = True
            if (self.threadLLM is not None) and self.threadLLM.is_alive():
                logger.info("Stopping active LLM thread")
                self.messenger.Lock()
                self.messenger.Put("/stop")
                self.messenger.Unlock()
            logger.info(f"Session {str(self.sessionName)} stop triggered")
        except Exception as e:
            logger.error(f"Session {str(self.sessionName)} stop FAILED. {str(e)}\n\ntraceback: {traceback.format_exc()}")
            pass
        return
    
    @atomic_transition("release")
    def Release(self):
        try:
            logger.info(f"Releasing session {self.sessionName}")
            if (self.threadLLM is not None) and self.threadLLM.is_alive():
                logger.info(f"Thread is still alive while releasing session {self.sessionName}, TERMINATE NOW.")
                StopThread(self.threadLLM)
            if self.clientPool is not None:
                logger.info(f"Destroy client pool.")
                self.clientPool.Destroy()
            self.threadLLM = None
            self.processor = None
            self.llmPool = None
            self.messenger = None
            self.alogger = None
            self.config = None
            self.title = None
            logger.info(f"Session {str(self.sessionName)} released")
        except Exception as e:
            logger.error(f"Session {str(self.sessionName)} release FAILED. {str(e)}\n\ntraceback: {traceback.format_exc()}")
            pass
        return
    
    def IsStopped(self) -> bool:
        return ((self.threadLLM is None) or (not self.threadLLM.is_alive())) and (0 == self.streamNum)
    
    def InitSpeech(self, clientPool):
        if self.config.speechOn:
            import sounddevice as sd
            logger.info("Initializing speech module")
            self.speech = clientPool.GetClient(self.config.services['speech']['addr'])
            logger.info("Preparing speech recognition and TTS models. This may include downloading weight data.")
            with self.speech.Timeout(-1):
                self.speech.PrepareModel()
            logger.info("Speech module model preparation completed")
            
            if any([re.fullmatch(r"(cuda|cpu)(:(\d+))?", s) == None for s in [self.config.ttsDevice, self.config.sttDevice]]):
                error_msg = "The value of ttsDevice and sttDevice should be a valid cuda device, such as cuda, cuda:0, or cpu, the default is cpu."
                logger.error(error_msg)
                exit(-1)
            else:
                self.speech.SetDevices({"tts": self.config.ttsDevice, "stt": self.config.sttDevice})
                logger.info(f"Speech devices set: TTS={self.config.ttsDevice}, STT={self.config.sttDevice}")
        else:
            self.speech = None
            logger.debug("Speech module not enabled")
        return
    
    @atomic_transition("desc")
    def Description(self) -> dict[str, str]:
        logger.info(f"Get decription of session {self.sessionName}")
        return {"sessionName": self.sessionName, "title": self.title, "state": self.state}
    
    @atomic_transition("stream")
    def MsgStream(self) -> typing.Generator:
        if self.stopFlag:
            return
        
        self.streamNum += 1
        
        try:
            buffer = self.alogger.Get(getBuffer=True)
            if len(buffer) > 0:
                yield f"data: {json.dumps(buffer)}\n\n"
        
            while (not self.stopFlag):
                try:
                    msg = self.alogger.Get(timeout=1)
                except Empty as e:
                    continue
                yield f"data: {json.dumps(msg)}\n\n"
        except Exception as e:
            error_msg = {"error": f"Stream error: {e}", "type": "error"}
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps(error_msg)}\n\n"
        finally:
            self.streamNum -= 1
    
    @atomic_transition("input")
    def Message(self, msg: str):
        logger.info(f"Chat request received in session {self.sessionName}")
        logger.debug(f"Message content: {msg[:50]}..." if len(msg) > 50 else f"Message content: {msg}")
        
        if self.title in [None, "New Chat"]:
            self.title = msg
        
        logger.info(f"Generating response for message in session {self.sessionName}")

        def response(msg: str):
            try:
                self.processor(msg)
            except Exception as e:
                pass
            finally:
                if "generating" == self.state:
                    self.answered()
                self.Save()
        
        self.processor.SetGas(1e8)
        self.threadLLM = threading.Thread(target=response, args=(msg,))
        self.threadLLM.start()
        return
    
    @atomic_transition("upload")
    def UploadFile(self, fileName: str, fileData: bytes, contentType: str) -> str:
        filename = secure_filename(fileName)
        filepath = os.path.join(self.sessionPath, "uploads", filename)
        with open(filepath, 'wb') as f:
            f.write(fileData)
        logger.info(f"{contentType} file '{filename}' uploaded to {filepath}")
        return filepath
    
    @atomic_transition("interrupt")
    def Interrupt(self):
        logger.info(f"Interrupting session {self.sessionName}")
        self.messenger.Lock()
        return
    
    @atomic_transition("sendmsg")
    def SendMsg(self, msg: str):
        logger.info(f"Sending message to session {self.sessionName}")
        logger.debug(f"Message content: {msg[:50]}..." if len(msg) > 50 else f"Message content: {msg}")
        self.messenger.Put(msg)
        self.messenger.Unlock()
        return
    
    def Proxy(self, href: str, method: str) -> typing.Generator:
        logger.debug(f"Proxy request for {href} with method {method}")
        var = self.processor.interpreter.env.get(href, None)
        if var and (type(var).__name__ in ['AImage', 'AVideo']):
            logger.debug(f"Proxy request resolved as variable of type {type(var).__name__}")
            yield {"type": "variable", "data": var}
        else:
            logger.debug(f"Proxy request forwarded to computer module")
            computer = self.processor.services['computer']
            res = computer.Proxy(href, method)
            responseInfo = next(res)
            yield {"type": "href", "responseInfo": responseInfo}
            yield from res