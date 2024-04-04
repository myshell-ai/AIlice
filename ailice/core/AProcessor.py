import time
import inspect
import re
from functools import partial
from ailice.common.AConfig import config
from ailice.core.llm.ALLMPool import llmPool
from ailice.common.APrompts import promptsManager
from ailice.common.ARemoteAccessors import clientPool
from ailice.common.AMessenger import messenger
from ailice.core.AConversation import AConversations
from ailice.core.AInterpreter import AInterpreter
from ailice.prompts.ARegex import ARegexMap


class AProcessor():
    def __init__(self, name, modelID, promptName, outputCB, collection = None):
        self.name = name
        self.modelID = modelID
        self.llm = llmPool.GetModel(modelID)
        self.interpreter = AInterpreter()
        self.conversation = AConversations()
        self.subProcessors = dict()
        self.modules = {}
        
        self.RegisterModules([config.services['storage']['addr']])
        self.interpreter.RegisterAction("CALL", {"func": self.EvalCall})
        self.interpreter.RegisterAction("RESPOND", {"func": self.EvalRespond})
        self.interpreter.RegisterAction("COMPLETE", {"func": self.EvalComplete})
        self.interpreter.RegisterAction("STORE", {"func": self.EvalStore})
        self.interpreter.RegisterAction("QUERY", {"func": self.EvalQuery})
        self.interpreter.RegisterAction("WAIT", {"func": self.EvalWait})
        
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
        ret = []
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
            for actionName, actionMeta in info["ACTIONS"].items():
                ret.append({"action": actionName, "signature": str(inspect.signature(getattr(module, actionMeta['func']))), "prompt": actionMeta["prompt"]})
                self.RegisterAction(nodeType=actionName, action={"func": self.CreateActionCB(actionName, module, actionMeta["func"])})
        return ret
    
    def CreateActionCB(self, actionName, module, actionFunc):
        func = getattr(module, actionFunc)
        def callback(*args,**kwargs):
            return func(*args,**kwargs)
        newSignature = inspect.Signature(parameters=[inspect.Parameter(name=t.name, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=t.annotation) for p,t in inspect.signature(func).parameters.items()],
                                         return_annotation=inspect.signature(func).return_annotation)
        callback.__signature__ = newSignature
        return callback
        
    def GetPromptName(self) -> str:
        return self.prompt.PROMPT_NAME
    
    def __call__(self, txt: str) -> str:
        self.conversation.Add(role = "USER", msg = txt, env = self.interpreter.env)
        self.EvalStore(txt)
        self.outputCB("<")
        self.outputCB(f"USER_{self.name}", txt)

        while True:
            prompt = self.prompt.BuildPrompt()
            ret = self.llm.Generate(prompt, proc=partial(self.outputCB, "ASSISTANT_" + self.name), endchecker=self.interpreter.EndChecker, temperature = config.temperature)
            self.conversation.Add(role = "ASSISTANT", msg = ret, env = self.interpreter.env)
            self.EvalStore(ret)
            self.result = ret
            
            msg = messenger.GetPreviousMsg()
            if msg != None:
                resp = f"Interruption. Reminder from super user: {msg}"
                self.conversation.Add(role = "SYSTEM", msg = resp, env = self.interpreter.env)
                self.EvalStore(resp)
                self.outputCB(f"SYSTEM_{self.name}", resp)
                continue
            
            resp = self.interpreter.EvalEntries(ret)
            
            if "" != resp:
                self.interpreter.EvalVar(varName="returned_content_in_last_function_call", content=resp)
                self.conversation.Add(role = "SYSTEM", msg = "This is a message automatically generated by the function you just called to return the result. Function returned: {" + resp + "}", env = self.interpreter.env)
                self.EvalStore("Function returned: {" + resp + "}")
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
            matches = [m for m in re.findall(f'<&\\|({ARegexMap["ref"]})\\|&>', msg)]
            for varName in matches:
                if varName in self.interpreter.env:
                    self.subProcessors[agentName].interpreter.env[varName] = self.interpreter.env[varName]
                else:
                    return f"variable name {varName} not defined in current env. please check and correct."
        
        resp = f"Agent {agentName} returned: {self.subProcessors[agentName](msg)}"

        matches = [m for m in re.findall(f'<&\\|({ARegexMap["ref"]})\\|&>', resp)]
        for varName in matches:
            if varName in self.subProcessors[agentName].interpreter.env:
                self.interpreter.env[varName] = self.subProcessors[agentName].interpreter.env[varName]
        return resp
    
    def EvalRespond(self, message: str) -> str:
        self.result = message
        return ""
    
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
    
    def EvalWait(self, duration: int) -> str:
        time.sleep(duration)
        return f"Waiting is over. It has been {duration} seconds."
    
    def EnvSummary(self) -> str:
        return "\n".join([f"{varName}: {type(var).__name__}  {str(var)[:50]}{'...[The remaining content is not shown]' if len(str(var)) > 50 else ''}" for varName, var in self.interpreter.env.items()]) + \
            ("\nTo save context space, only the first fifty characters of each variable are shown here. You can use the PRINT function to view its complete contents." if self.interpreter.env else "")
    
    def ToJson(self) -> str:
        return {"name": self.name,
                "modelID": self.modelID,
                "conversations": self.conversation.ToJson(),
                "subProcessors": {k: p.ToJson() for k, p in self.subProcessors.items()},
                "modules": {k:{'addr': m['addr']} for k, m in self.modules.items()},
                "collection": self.collection}