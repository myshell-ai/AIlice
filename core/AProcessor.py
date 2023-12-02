import time
from functools import partial
from common.AConfig import config
from llm.ALLMPool import llmPool
from prompts.APrompts import promptsManager
from modules.ARemoteAccessors import clientPool, Storage
from core.AConversation import AConversations
from core.AInterpreter import AInterpreter

class AProcessor():
    def __init__(self, name, modelID, promptName, outputCB, collection = None):
        self.name = name
        self.modelID = modelID
        self.llm = llmPool.GetModel(modelID)
        self.interpreter = AInterpreter()
        self.conversation = AConversations()
        self.subProcessors = dict()
        self.modules = {}
        
        self.RegisterModules([Storage])
        self.interpreter.RegisterAction("CALL", {"func": self.EvalCall})
        self.interpreter.RegisterAction("RESPOND", {"func": self.EvalRespond})
        self.interpreter.RegisterAction("COMPLETE", {"func": self.EvalComplete})
        self.interpreter.RegisterAction("STORE", {"func": self.EvalStore})
        self.interpreter.RegisterAction("QUERY", {"func": self.EvalQuery})
        
        self.outputCB = outputCB
        self.collection = "ailice" + str(time.time()) if collection is None else collection
        self.prompt = promptsManager[promptName](processor=self, storage=self.modules['storage']['module'], collection=self.collection, conversations=self.conversation, formatter=self.llm.formatter, outputCB=self.outputCB)
        for nodeType, action in self.prompt.GetActions().items():
            self.interpreter.RegisterAction(nodeType, action)
        for nodeType, patterns in self.prompt.GetPatterns().items():
            for p in patterns:
                self.interpreter.RegisterPattern(nodeType, p["re"], p["isEntry"])
        self.result = "None."
        return
    
    def RegisterAction(self, nodeType: str, action: dict):
        self.interpreter.RegisterAction(nodeType, action)
        return
    
    def RegisterModules(self, moduleAddrs):
        for moduleAddr in moduleAddrs:
            module = clientPool.GetClient(moduleAddr)
            if (not hasattr(module, "ModuleInfo")) or (not callable(getattr(module, "ModuleInfo"))):
                raise Exception("EXCEPTION: ModuleInfo() not found in module.")
            info = module.ModuleInfo()
            if "NAME" not in info:
                raise Exception("EXCEPTION: 'NAME' is not found in module info.")
            if "ACTIONS" not in info:
                raise Exception("EXCEPTION: 'ACTIONS' is not found in module info.")
            
            self.modules[info['NAME']] = {'addr': moduleAddr, 'module': module}
            for actionName, actionSig in info["ACTIONS"].items():
                actionFunc = actionSig["sig"][:actionSig["sig"].find("(")]
                self.RegisterAction(nodeType=actionName, action={"func": self.CreateActionCB(actionName, module, actionFunc),
                                                                 "signatureExpr": actionSig["sig"]})
        return
    
    def CreateActionCB(self, actionName, module, actionFunc):
        def callback(*args,**kwargs):
            return f"{actionName}_RESULT=[{getattr(module, actionFunc)(*args,**kwargs)}]"
        return callback
        
    def GetPromptName(self) -> str:
        return self.prompt.PROMPT_NAME
    
    def __call__(self, txt: str) -> str:
        self.conversation.Add(role = "USER", msg = txt)
        self.outputCB("<")
        self.outputCB(f"USER_{self.name}", txt)

        while True:
            prompt = self.prompt.BuildPrompt()
            ret = self.llm.Generate(prompt, proc=partial(self.outputCB, "ASSISTANT_" + self.name), endchecker=self.interpreter.EndChecker, temperature = config.temperature)
            self.conversation.Add(role = "ASSISTANT", msg = ret)
            self.result = ret
            
            resp = self.interpreter.EvalEntries(ret)
            
            if "" != resp:
                self.conversation.Add(role = "SYSTEM", msg = "Function returned: {" + resp + "}")
                self.outputCB(f"SYSTEM_{self.name}", resp)
            else:
                self.outputCB(">")
                return self.result

    def EvalCall(self, agentType: str, agentName: str, msg: str) -> str:
        if agentType not in promptsManager:
            return f"CALL FAILED. specified agentType {agentType} does not exist. This may be caused by using an agent type that does not exist or by getting the parameters in the wrong order."
        if (agentName not in self.subProcessors) or (agentType != self.subProcessors[agentName].GetPromptName()):
            self.subProcessors[agentName] = AProcessor(name=agentName, modelID=self.modelID, promptName=agentType, outputCB=self.outputCB, collection=self.collection)
            self.subProcessors[agentName].RegisterModules([self.modules[moduleName]['addr'] for moduleName in self.modules])
        resp = f"Agent {agentName} returned: {self.subProcessors[agentName](msg)}"
        return resp
    
    def EvalRespond(self, message: str):
        self.result = message
        return
    
    def EvalStore(self, txt: str):
        if not self.modules['storage']['module'].Store(self.collection, txt):
            return "STORE FAILED, please check your input."
        return
    
    def EvalQuery(self, keywords: str) -> str:
        res = self.modules['storage']['module'].Query(self.collection, keywords)
        if (0 == len(res)) or (res[0][1] > 0.5):
            return "Nothing found."
        return "QUERY_RESULT={" + res[0][0] +"}"
    
    def EvalComplete(self, result: str):
        self.result = result
        self.prompt.Reset()
        return