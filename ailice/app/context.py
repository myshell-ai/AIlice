import os
import time
import json
import copy
import threading
import shutil
from transitions.extensions import LockedMachine

from ailice.common.AConfig import AConfig
from ailice.common.AConfig import config as global_config
from ailice.common.lightRPC import GenerateCertificates

from ailice.app.decorators import atomic_transition
from ailice.app.task import TaskSession
from ailice.app.config import AiliceWebConfig
from ailice.app.schema import apply_patches, build_settings_schema, check_path, validate_patches
from ailice.app.log import logger
from ailice.app.cleaner import cleaner
from ailice.app.exceptions import *



class UserContext():
    states = ['init', 'ready', 'released']
    settings = ["agentModelConfig", "models", "temperature", "contextWindowRatio"]
    allowedPathes = [["agentModelConfig"],
                     ["models", ["oai", "groq", "openrouter", "apipie", "deepseek", "mistral", "anthropic"], "apikey"],
                     ["temperature"],
                     ["contextWindowRatio"]]
    
    def __init__(self, userID: str):
        self.userID = userID
        self.config = AConfig()
        self.currentSession = None
        self.context = dict()
        self.speech = None
        self.methodLock = threading.RLock()
        self.machine = LockedMachine(model=self, states=UserContext.states, initial='init')
        self.machine.add_transition(trigger='create', source='init', dest='ready')
        self.machine.add_transition(trigger='release', source='*', dest='released')
        self.machine.add_transition(trigger='session_call', source='ready', dest='ready')
        self.serverPublicFile = None
        self.serverSecretFile = None
        self.serverPublicFile = None
        self.serverSecretFile = None
        logger.debug(f"UserContext initialized for user ID: {userID}")
        return

    def GetPath(self, pathType: str="", sessionName: str=""):
        pathes = {"": "",
                  "user_config": "user_config.json",
                  "certificates": "certificates",
                  "sessions": "sessions",
                  "session": f"sessions/{sessionName}",
                  "history": f"sessions/{sessionName}/ailice_history.json"}
        return os.path.join(self.config.chatHistoryPath, str(self.userID), pathes[pathType])
    
    def StoreConfig(self):
        userCfg = {"agentModelConfig": self.config.agentModelConfig,
                   "models": {providerName: {k: v for k, v in providerCfg.items() if k!="modelList"} for providerName, providerCfg in self.config.models.items() if providerName not in ["default"]},
                   "temperature": self.config.temperature,
                   "contextWindowRatio": self.config.contextWindowRatio}
        
        config_path = self.GetPath(pathType="user_config")
        with open(config_path, "w") as f:
            json.dump(userCfg, f, indent=2)
        logger.info(f"User configuration stored to {config_path}")
        return
    
    def UpdateConfig(self, updatedConfig):
        logger.info(f"Updating configuration for user {self.userID}")
        if "agentModelConfig" in updatedConfig:
            self.config.agentModelConfig = updatedConfig["agentModelConfig"]
            logger.debug("Updated agentModelConfig")
        if "models" in updatedConfig:
            #protect the models in config from being modified.
            updateModels = {providerName: providerCfg for providerName, providerCfg in updatedConfig["models"].items() if providerName not in ["default"]}
            for providerName in updateModels:
                updateModels[providerName]["modelList"] = self.config.models[providerName]["modelList"]
            self.config.models.update(updateModels)
            logger.debug(f"Updated models configuration for providers: {list(updateModels.keys())}")
        if "temperature" in updatedConfig:
            self.config.temperature = float(updatedConfig["temperature"])
            logger.debug(f"Updated temperature to {self.config.temperature}")
        if "contextWindowRatio" in updatedConfig:
            self.config.contextWindowRatio = float(updatedConfig["contextWindowRatio"])
            logger.debug(f"Updated contextWindowRatio to {self.config.contextWindowRatio}")
        return
        
    def InitConfig(self):
        logger.info(f"Initializing configuration for user {self.userID}")
        self.config.__dict__.update(copy.deepcopy(global_config.ToJson()))
        
        configFile = self.GetPath(pathType="user_config")
        userConfig = {}
        if os.path.exists(configFile):
            with open(configFile, "r") as f:
                userConfig = json.load(f)
                logger.info(f"Loaded user configuration from {configFile}")
        else:
            logger.info(f"No user configuration found at {configFile}, using defaults")
        self.UpdateConfig(userConfig)
        return
    
    @atomic_transition("create")
    def Create(self):
        logger.info(f"Creating user context for user {self.userID}")
        os.makedirs(self.GetPath(), exist_ok=True)
        os.makedirs(self.GetPath("sessions"), exist_ok=True)

        self.InitConfig()
        self.serverPublicFile, self.serverSecretFile = GenerateCertificates(self.GetPath(pathType="certificates"), "server")
        self.clientPublicFile, self.clientSecretFile = GenerateCertificates(self.GetPath(pathType="certificates"), "client")
        logger.info("Certificates generated")
        return
    
    @atomic_transition("release")
    def Release(self):
        logger.info(f"Releasing user context for user {self.userID}")
        for sessionName, session in self.context.items():
            logger.info(f"Releasing session {sessionName}")
            session.Stop()
            cleaner.AddSessionToGC(sessionName, session)
        self.context.clear()
        return
    
    @atomic_transition("session_call")
    def Setup(self, patches: list, apply = False) -> dict:
        updatedConfig = self.config.__dict__

        if (patches is not None) and (type(patches) is list) and (len(patches) > 0):
            logger.info(f"Setting up user context with patches: {patches}")
            try:
                validatedPatches = validate_patches(patches=patches)
                logger.debug("Patches validated")
            except Exception as e:
                logger.error(f"Setup() Exception: Invalid patches input. {patches}", exc_info=True)
                raise AWExceptionIllegalInput()
            
            if not all([any([check_path(p["path"], pattern) for pattern in UserContext.allowedPathes]) for p in patches]):
                logger.error(f"Setup() Exception. Invalid path input: {patches}")
                raise AWExceptionIllegalInput()
            
            updatedConfig = apply_patches(self.config.__dict__, validatedPatches)
            logger.debug("Patches applied to configuration")

            try:
                AiliceWebConfig.model_validate({k: v for k,v in updatedConfig.items() if k in UserContext.settings})
                logger.debug("Configuration validated")
            except Exception as e:
                logger.error(f"Configuration validation failed: {str(e)}", exc_info=True)
                raise

            for k, v in updatedConfig.items():
                if "agentModelConfig" == k:
                    modelIDs = [f"{modelType}:{model}" for modelType in self.config.models for model in self.config.models[modelType]["modelList"]]
                    if any([(mid not in modelIDs) for agentType, mid in v.items()]):
                        logger.error(f"Setup() Exception. Invalid modelID input: {patches}")
                        raise AWExceptionIllegalInput()
            
            if apply:
                self.UpdateConfig(updatedConfig)
                self.StoreConfig()
            
                for sessionName, session in self.context.items():
                    logger.info(f"Releasing session {sessionName} due to configuration update")
                    session.Stop()
                    cleaner.AddSessionToGC(sessionName, session)
                self.context.clear()
                
                sessionName = self.currentSession
                self.currentSession = None
                if sessionName is not None:
                    logger.info(f"Reloading current session {sessionName}")
                    self.Load(sessionName)
        
        ret = {}
        for k in UserContext.settings:
            if k == "models":
                ret[k] = {provider: ({"modelWrapper": providerCfg["modelWrapper"],
                                      "apikey": None,
                                      "baseURL": None,
                                      #protect the default model settings.
                                      "modelList": providerCfg["modelList"]} if provider in ["default"] else providerCfg) for provider, providerCfg in (self.config.__dict__[k].items() if apply else updatedConfig[k].items())}
            else:
                ret[k] = (self.config.__dict__[k] if apply else updatedConfig[k])
        logger.debug("Settings schema built")
        return build_settings_schema(ret)

    @atomic_transition("session_call")
    def CurrentSession(self):
        if not self.currentSession:
            logger.warning(f"No current session for user {self.userID}")
            raise AWExceptionSessionNotExist()
        logger.debug(f"Returning current session {self.currentSession}")
        return self.context[self.currentSession]

    def Load(self, sessionName: str):
        logger.info(f"Loading session {sessionName} for user {self.userID}")
        try:
            if sessionName == self.currentSession:
                logger.info(f"Session {sessionName} already loaded, return now.")
                return
            
            logger.info(f"Release session {self.currentSession} at {self.GetPath(pathType='session', sessionName=self.currentSession)}")
            if self.currentSession in self.context:
                self.context[self.currentSession].Stop()
                cleaner.AddSessionToGC(self.currentSession, self.context[self.currentSession])
                self.context.pop(self.currentSession)
            self.currentSession = None
            
            sessionPath = self.GetPath(pathType="session", sessionName=sessionName)
            logger.info(f"Creating new TaskSession for {sessionName} at {sessionPath}")
            if cleaner.IsSessionInGC(sessionName) and (not time.sleep(5)) and cleaner.IsSessionInGC(sessionName):
                raise AWExceptionSessionBusy()
            self.context[sessionName] = TaskSession(sessionName, sessionPath, self.clientSecretFile, self.serverPublicFile)
            self.context[sessionName].Create(config=self.config)
            self.currentSession = sessionName
            logger.info(f"Session {sessionName} loaded successfully")
        except Exception as e:
            logger.error(f"Exception loading session {sessionName}: {str(e)}, currentSession: {self.currentSession}", exc_info=True)
            if hasattr(e, 'tb'):
                logger.error(e.tb)
            if sessionName in self.context:
                logger.info(f"Cleaning up failed session {sessionName}")
                self.context[sessionName].Stop()
                cleaner.AddSessionToGC(sessionName, self.context[sessionName])
                self.context.pop(sessionName)
                raise e
        return
    
    @atomic_transition("session_call")
    def NewSession(self) -> str:
        sessionName = "ailice_" + str(int(time.time()))
        logger.info(f"Creating new session {sessionName} for user {self.userID}")
        self.Load(sessionName=sessionName)
        return sessionName
    
    @atomic_transition("session_call")
    def LoadSession(self, sessionName: str):
        logger.info(f"Loading session history for {sessionName}")
        sessions_dir = self.GetPath(pathType="sessions")
        if sessionName not in os.listdir(sessions_dir):
            logger.error(f"Session {sessionName} not found in {sessions_dir}")
            raise AWExceptionSessionNotExist()
        
        needLoading = (sessionName != self.currentSession)
        if needLoading:
            logger.info(f"Session {sessionName} is not current, loading it")
            self.Load(sessionName=sessionName)
        return
    
    @atomic_transition("session_call")
    def GetSession(self, sessionName: str):
        logger.info(f"Getting session history for {sessionName}")
        sessions_dir = self.GetPath(pathType="sessions")
        if sessionName not in os.listdir(sessions_dir):
            logger.error(f"Session {sessionName} not found in {sessions_dir}")
            raise AWExceptionSessionNotExist()
        
        def historyFilter(data):
            conversations = [(f"{conv['role']}_{data['name']}", conv['msg']) for conv in data['conversation']]
            ret = {"conversation": conversations}
            if 'subProcessors' in data:
                ret["subProcessors"] = {agentName: historyFilter(subProcessor) for agentName, subProcessor in data['subProcessors'].items()}
            else:
                ret["subProcessors"] = {}
            return ret
        
        historyPath = self.GetPath(pathType="history", sessionName=sessionName)
        if os.path.exists(historyPath):
            with open(historyPath, "r") as f:
                data = json.load(f)
                conversations = historyFilter(data)
                logger.info(f"Got {len(conversations)} conversation entries from {historyPath}")
        else:
            logger.info(f"No history file found at {historyPath}, returning empty conversation")
            conversations = {}
        return conversations
    
    @atomic_transition("session_call")
    def DeleteSession(self, sessionName: str) -> bool:
        logger.info(f"Deleting session {sessionName} for user {self.userID}")
        if sessionName in self.context:
            logger.info(f"Releasing active session {sessionName}")
            self.context[sessionName].Stop()
            cleaner.AddSessionToGC(sessionName, self.context[sessionName])
            self.context.pop(sessionName)
            self.currentSession = None if sessionName == self.currentSession else self.currentSession
        
        sessions_dir = self.GetPath(pathType="sessions")
        if sessionName not in os.listdir(sessions_dir):
            logger.warning(f"Session {sessionName} not found in {sessions_dir}")
            return False
        historyDir = self.GetPath(pathType="session", sessionName=sessionName)
        shutil.rmtree(historyDir)
        logger.info(f"Deleted session directory {historyDir}")
        return True
    
    @atomic_transition("session_call")
    def ListSessions(self):
        logger.info(f"Listing sessions for user {self.userID}")
        histories = []
        sessions_dir = self.GetPath(pathType="sessions")
        for d in os.listdir(sessions_dir):
            p = self.GetPath(pathType="history", sessionName=d)
            if os.path.exists(p) and (os.path.getsize(p) > 0):
                with open(p, "r") as f:
                    try:
                        content = json.load(f)
                        if len(content.get('conversation', [])) > 0:
                            histories.append((d, content.get('conversation')[0]['msg']))
                    except Exception as e:
                        logger.error(f"Error loading history file {p}: {str(e)}", exc_info=True)
                        continue
        sorted_histories = sorted(histories, key=lambda x: os.path.getmtime(self.GetPath(pathType="history", sessionName=x[0])), reverse=True)
        logger.info(f"Found {len(sorted_histories)} sessions")
        return sorted_histories