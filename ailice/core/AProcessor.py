import sys
import string
import secrets
import importlib
import time
import inspect
import re
import random
import json
from ailice.common.AConfig import config
from ailice.common.utils.ALogger import ALoggerSection, ALoggerMsg
from ailice.core.AConversation import AConversations
from ailice.core.AInterpreter import AInterpreter
from ailice.prompts.ARegex import GenerateRE4FunctionCalling, FUNCTION_CALL_DEFAULT


class AProcessor():
    def __init__(self, name, modelID, promptName, llmPool, promptsManager, services, messenger, outputCB, collection = None):
        self.name = name
        self.modelID = modelID
        self.llmPool = llmPool
        self.llm = llmPool.GetModel(modelID, promptName)
        self.promptsManager = promptsManager
        self.services = services
        self.messenger = messenger
        self.interpreter = AInterpreter(messenger)
        self.conversation = AConversations()
        self.subProcessors = dict()
        self.modules = {}
        self.outputCB = outputCB
        self.collection = "ailice" + str(time.time()) if collection is None else collection
        
        self.RegisterModules([config.services['storage']['addr']])
        self.interpreter.RegisterAction("CALL", {"func": self.EvalCall})
        self.interpreter.RegisterAction("RESPOND", {"func": self.EvalRespond})
        self.interpreter.RegisterAction("RETURN", {"func": self.Return})
        self.interpreter.RegisterAction("STORE", {"func": self.EvalStore})
        self.interpreter.RegisterAction("QUERY", {"func": self.EvalQuery})
        self.interpreter.RegisterAction("WAIT", {"func": self.EvalWait})
        self.interpreter.RegisterAction("DEFINE-CODE-VARS", {"func": self.DefineCodeVars})
        self.interpreter.RegisterAction("LOADEXTMODULE", {"func": self.LoadExtModule})
        self.interpreter.RegisterAction("LOADEXTPROMPT", {"func": self.LoadExtPrompt})
        
        self.prompt = promptsManager[promptName](processor=self, storage=self.modules['storage']['module'], collection=self.collection, conversations=self.conversation, formatter=self.llm.formatter, outputCB=self.outputCB)
        self.result = "None."

        self.modules['storage']['module'].Store(self.collection + "_functions", json.dumps({"module": "core",
                                                                                            "action": "LOADEXTMODULE",
                                                                                            "signature": "LOADEXTMODULE<!|addr: str|!> -> str",
                                                                                            "prompt": "Load the ext-module and get the list of callable functions in it. ",
                                                                                            "type": "primary"}))
        self.modules['storage']['module'].Store(self.collection + "_functions", json.dumps({"module": "core",
                                                                                            "action": "LOADEXTPROMPT",
                                                                                            "signature": "LOADEXTPROMPT<!|path: str|!> -> str",
                                                                                            "prompt": "Load ext-prompt from the path pointing to python source code file, which include available new agent type.",
                                                                                            "type": "primary"}))
        return
    
    def RegisterAction(self, nodeType: str, action: dict):
        self.interpreter.RegisterAction(nodeType, action)
        return
    
    def RegisterModules(self, moduleAddrs):
        ret = []
        modules = {}
        funcList = []
        actions = {}
        for moduleAddr in moduleAddrs:
            module = self.services.GetClient(moduleAddr)
            if (not hasattr(module, "ModuleInfo")) or (not callable(getattr(module, "ModuleInfo"))):
                raise Exception("EXCEPTION: ModuleInfo() not found in module.")
            info = module.ModuleInfo()
            if "NAME" not in info:
                raise Exception("EXCEPTION: 'NAME' is not found in module info.")
            if "ACTIONS" not in info:
                raise Exception("EXCEPTION: 'ACTIONS' is not found in module info.")
            
            modules[info['NAME']] = {'addr': moduleAddr, 'module': module}
            for actionName, actionMeta in info["ACTIONS"].items():
                sig = actionName + str(inspect.signature(getattr(module, actionMeta['func']))).replace('(', '<!|').replace(')', '|!>')
                ret.append({"action": actionName, "signature": sig, "prompt": actionMeta["prompt"]})
                actions[actionName] = {"func": self.CreateActionCB(actionName, module, actionMeta["func"])}
                funcList.append(json.dumps({"module": info["NAME"], "action": actionName, "signature": sig, "prompt": actionMeta["prompt"], "type": actionMeta["type"]}))
        self.modules.get('storage', modules.get('storage', None))['module'].Store(self.collection + "_functions", funcList)
        for actionName, action in actions.items():
            self.RegisterAction(nodeType=actionName, action=action)
        self.modules.update(modules)
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
    
    def Prepare(self):
        self.RegisterModules(set(self.services.pool) - set([d['addr'] for name, d in self.modules.items()]))
        for nodeType, action in self.prompt.GetActions().items():
            self.interpreter.RegisterAction(nodeType, action)
        for nodeType, patterns in self.prompt.GetPatterns().items():
            for p in patterns:
                self.interpreter.RegisterPattern(nodeType, p["re"], p["isEntry"])
        self.interpreter.RegisterPattern("_FUNCTION_CALL_DEFAULT", FUNCTION_CALL_DEFAULT, True, True, 99999999)
        self.interpreter.RegisterAction("_FUNCTION_CALL_DEFAULT", {"func": self.EvalFunctionCallDefault, "noEval": ["funcName", "paras"]})
        return
    
    def __call__(self, txt: str) -> str:
        self.conversation.Add(role = "USER", msg = txt, env = self.interpreter.env, entry=True)
        self.EvalStore(txt)
        with ALoggerSection(recv=self.outputCB) as loggerSection:
            loggerSection(f"USER_{self.name}", txt)

            while True:
                self.Prepare()
                prompt = self.prompt.BuildPrompt()
                with ALoggerMsg(recv=self.outputCB, channel="ASSISTANT_" + self.name) as loggerMsg:
                    ret = self.llm.Generate(prompt, proc=loggerMsg, endchecker=self.interpreter.EndChecker, temperature = config.temperature)
                self.conversation.Add(role = "ASSISTANT", msg = ret, env = self.interpreter.env)
                self.EvalStore(ret)
                self.result = ret
                
                msg = self.messenger.GetPreviousMsg()
                if msg != None:
                    resp = f"Interruption. Reminder from super user: {msg}"
                    self.conversation.Add(role = "SYSTEM", msg = resp, env = self.interpreter.env)
                    self.EvalStore(resp)
                    loggerSection(f"SYSTEM_{self.name}", resp)
                    continue
                
                resp = self.interpreter.EvalEntries(ret)
                
                if "" != resp:
                    self.interpreter.EvalVar(varName="returned_content_in_last_function_call", content=resp)
                    self.conversation.Add(role = "SYSTEM", msg = "This is a system-generated message. Since the function call in your previous message has returned information, the response to this message will be handled by the backend system instead of the user. Meanwhile, your previous message has been marked as private and has not been sent to the user. Function returned: {" + resp + "}\n\nThe returned text has been automatically saved to variable 'returned_content_in_last_function_call' for quick reference.", env = self.interpreter.env)
                    self.EvalStore("Function returned: {" + resp + "}")
                    loggerSection(f"SYSTEM_{self.name}", resp)
                else:
                    return self.result

    def EvalCall(self, agentType: str, agentName: str, msg: str) -> str:
        if agentType not in self.promptsManager:
            return f"CALL FAILED. specified agentType {agentType} does not exist. This may be caused by using an agent type that does not exist or by getting the parameters in the wrong order."
        if (agentName not in self.subProcessors) or (agentType != self.subProcessors[agentName].GetPromptName()):
            self.subProcessors[agentName] = AProcessor(name=agentName, modelID=self.modelID, promptName=agentType, llmPool=self.llmPool, promptsManager=self.promptsManager, services=self.services, messenger=self.messenger, outputCB=self.outputCB, collection=self.collection)
            self.subProcessors[agentName].RegisterModules([self.modules[moduleName]['addr'] for moduleName in self.modules])
        
        for varName in self.interpreter.env:
            if varName in msg:
                self.subProcessors[agentName].interpreter.env[varName] = self.interpreter.env[varName]
        
        resp = f"Agent {agentName} returned: {self.subProcessors[agentName](msg)}"

        for varName in self.subProcessors[agentName].interpreter.env:
            if varName in resp:
                self.interpreter.env[varName] = self.subProcessors[agentName].interpreter.env[varName]
        return resp
    
    def EvalRespond(self, message: str) -> str:
        self.result = message
        return ""
    
    def EvalStore(self, txt: str):
        self.modules['storage']['module'].Store(self.collection, txt)
        return
    
    def EvalQuery(self, query: str) -> str:
        res = self.modules['storage']['module'].Recall(collection=self.collection, query=query)
        return f"QUERY_RESULT=[{res}]"
    
    def Return(self) -> str:
        return ""
    
    def EvalWait(self, duration: int) -> str:
        time.sleep(duration)
        return f"Waiting is over. It has been {duration} seconds."
    
    def DefineCodeVars(self) -> str:
        matches = re.findall(r"```(\w*)\n([\s\S]*?)```", self.conversation.GetConversations(frm=-1)[1]["msg"])
        vars = []
        for language, code in matches:
            varName = f"code_{language}_{str(random.randint(0,10000))}"
            self.interpreter.env[varName] = code
            vars.append(varName)
        if 0 < len(vars):
            return f"\nSystem notification: The code snippets within the triple backticks in last message have been saved as variables, in accordance with their order in the text, the variable names are as follows: {vars}\n"
        else:
            return "\nSystem notification: No code snippet found. Are you sure you wrapped them with triple backticks?"
    
    def LoadExtModule(self, addr: str) -> str:
        try:
            ret = self.RegisterModules([addr])
            prompts = []
            for r in ret:
                self.interpreter.RegisterPattern(nodeType=r['action'], pattern=GenerateRE4FunctionCalling(r['signature'], faultTolerance = False), isEntry=True)
                prompts.append(f"{r['signature']}: {r['prompt']}")
            ret = "\n".join(prompts)
        except Exception as e:
            ret = f"Exception: {str(e)}"
        return ret
    
    def LoadExtPrompt(self, path: str) -> str:
        ret = ""
        try:
            alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits
            symbol = "".join([secrets.choice(alphabet) for i in range(32)])

            moduleName = "APrompt_" + symbol
            spec = importlib.util.spec_from_file_location(moduleName, path)
            promptModule = importlib.util.module_from_spec(spec)
            sys.modules[moduleName] = promptModule
            spec.loader.exec_module(promptModule)
            
            ret += self.promptsManager.RegisterPrompts([promptModule.APrompt])
            if "" == ret:
                ret += f"Prompt module {promptModule.APrompt.PROMPT_NAME} has been loaded. Its description information is as follows:\n{promptModule.APrompt.PROMPT_DESCRIPTION}"
        except Exception as e:
            ret = f"Exception: {str(e)}"
        return ret
    
    def EvalFunctionCallDefault(self, funcName: str, paras: str) -> str:
        if funcName not in self.interpreter.actions:
            return f"Error: Function call detected, but function name '{funcName}' does not exist."
        else:
            return f"Error: The function call to '{funcName}' failed, please check whether the number and type of parameters are correct. For example, the session name/agent type/url need to be of str type, and the str type needs to be enclosed in quotation marks, etc."
    
    def EnvSummary(self) -> str:
        return "\n".join([f"{varName}: {type(var).__name__}  {str(var)[:50]}{'...[The remaining content is not shown]' if len(str(var)) > 50 else ''}" for varName, var in self.interpreter.env.items()]) + \
            ("\nTo save context space, only the first fifty characters of each variable are shown here. You can use the PRINT function to view its complete contents." if self.interpreter.env else "")
    
    def FromJson(self, data):
        self.name = data["name"]
        #self.modelID = data["modelID"]
        self.interpreter.FromJson(data['interpreter'])
        self.conversation.FromJson(data["conversation"])
        self.collection = data['collection']
        self.RegisterModules([m['addr'] for k,m in data["modules"].items()])
        self.prompt = self.promptsManager[data['agentType']](processor=self, storage=self.modules['storage']['module'], collection=self.collection, conversations=self.conversation, formatter=self.llm.formatter, outputCB=self.outputCB)
        if hasattr(self.prompt, "FromJson"):
            self.prompt.FromJson(data['prompt'])
        for agentName, state in data['subProcessors'].items():
            self.subProcessors[agentName] = AProcessor(name=agentName, modelID=self.modelID, promptName=state['agentType'], llmPool=self.llmPool, promptsManager=self.promptsManager, services=self.services, messenger=self.messenger, outputCB=self.outputCB, collection=self.collection)
            self.subProcessors[agentName].FromJson(state)
        return
    
    def ToJson(self):
        return {"name": self.name,
                "modelID": self.modelID,
                "agentType": self.prompt.PROMPT_NAME,
                "prompt": self.prompt.ToJson() if hasattr(self.prompt, "ToJson") else {},
                "interpreter": self.interpreter.ToJson(),
                "conversation": self.conversation.ToJson(),
                "collection": self.collection,
                "modules": {k:{'addr': m['addr']} for k, m in self.modules.items()},
                "subProcessors": {k: p.ToJson() for k, p in self.subProcessors.items()}}