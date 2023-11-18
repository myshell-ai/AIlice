import time
from common.AConfig import config
from llm.ALLMPool import llmPool
from prompts.APrompts import promptsManager
from modules.ARemoteAccessors import *
from core.AConversation import AConversations
from core.AInterpreter import AInterpreter

class AProcessor():
    def __init__(self, modelID, promptName, outputCB, collection = None):
        self.modelID = modelID
        self.llm = llmPool.GetModel(modelID)
        self.interpreter = AInterpreter()
        self.conversation = AConversations()
        self.subProcessors = dict()
        
        self.interpreter.RegisterAction("CALL", self.EvalCall)
        self.interpreter.RegisterAction("RESPOND", self.EvalRespond)
        self.interpreter.RegisterAction("STORE", self.EvalStore)
        self.interpreter.RegisterAction("QUERY", self.EvalQuery)
        self.interpreter.RegisterAction("ARXIV", self.EvalArxiv)
        self.interpreter.RegisterAction("SCROLLDOWNARXIV", self.EvalScrollDownArxiv)
        self.interpreter.RegisterAction("GOOGLE", self.EvalGoogle)
        self.interpreter.RegisterAction("SCROLLDOWNGOOGLE", self.EvalScrollDownGoogle)
        self.interpreter.RegisterAction("DUCKDUCKGO", self.EvalDuckDuckGo)
        self.interpreter.RegisterAction("SCROLLDOWNDUCKDUCKGO", self.EvalScrollDownDuckDuckGo)
        self.interpreter.RegisterAction("BROWSE", self.EvalBrowse)
        self.interpreter.RegisterAction("SCROLLDOWN", self.EvalScrollDown)
        self.interpreter.RegisterAction("BASH", self.EvalBashCode)
        self.interpreter.RegisterAction("SCROLLUPBASH", self.EvalScrollUpBash)
        self.interpreter.RegisterAction("PYTHON", self.EvalPythonCode)
        self.interpreter.RegisterAction("SCROLLUPPY", self.EvalScrollUpPy)
        self.interpreter.RegisterAction("COMPLETE", self.EvalComplete)
        
        self.outputCB = outputCB
        self.collection = "ailice" + str(time.time()) if collection is None else collection
        self.storage = makeClient(Storage)
        self.browser = makeClient(Browser)
        self.arxiv = makeClient(Arxiv)
        self.google = makeClient(Google)
        self.duckduckgo = makeClient(Duckduckgo)
        self.scripter = makeClient(Scripter)
        self.prompt = promptsManager[promptName](processor=self, storage=self.storage, collection=self.collection, conversations=self.conversation, formatter=llmPool.GetFormatter(modelID), outputCB=self.outputCB)
        for nodeType, func in self.prompt.GetActions().items():
            self.interpreter.RegisterAction(nodeType, func['func'])
        for nodeType, patterns in self.prompt.GetPatterns().items():
            for p in patterns:
                self.interpreter.RegisterPattern(nodeType, p["re"], p["isEntry"])
        self.result = "None."
        return
    
    def RegisterAction(self, nodeType: str, func: dict):
        self.interpreter.RegisterAction(nodeType, func)
        return
    
    def GetPromptName(self) -> str:
        return self.prompt.PROMPT_NAME
    
    def __call__(self, txt: str) -> str:
        self.conversation.Add(role = "USER", msg = txt)
        self.outputCB("<")
        self.outputCB("USER", txt)

        while True:
            prompt = self.prompt.BuildPrompt()
            ret = self.llm.Generate(prompt, proc=self.outputCB, endchecker=self.interpreter.EndChecker, temperature = config.temperature)
            self.conversation.Add(role = "ASSISTANT", msg = ret)
            self.result = ret
            
            resp = self.interpreter.EvalEntries(ret)
            
            if "" != resp:
                self.conversation.Add(role = "SYSTEM", msg = "Function returned: {" + resp + "}")
                self.outputCB("SYSTEM", resp)
            else:
                self.outputCB(">")
                return self.result

    def EvalCall(self, agentType: str, agentName: str, msg: str) -> str:
        if agentType not in promptsManager:
            return f"CALL FAILED. specified agentType {agentType} does not exist. This may be caused by using an agent type that does not exist or by getting the parameters in the wrong order."
        if (agentName not in self.subProcessors) or (agentType != self.subProcessors[agentName].GetPromptName()):
            self.subProcessors[agentName] = AProcessor(modelID=self.modelID, promptName=agentType, outputCB=self.outputCB, collection=self.collection)
        resp = f"Agent {agentName} returned: {self.subProcessors[agentName](msg)}"
        return resp
    
    def EvalRespond(self, message: str):
        self.result = message
        return
    
    def EvalStore(self, txt: str):
        if not self.storage.Store(self.collection, txt):
            return "STORE FAILED, please check your input."
        return
    
    def EvalQuery(self, keywords: str) -> str:
        res = self.storage.Query(self.collection, keywords)
        if (0 == len(res)) or (res[0][1] > 0.5):
            return "Nothing found."
        return "QUERY_RESULT={" + res[0][0] +"}"
    
    def EvalArxiv(self, keywords: str) -> str:
        return self.arxiv.ArxivSearch(keywords)
    
    def EvalScrollDownArxiv(self) -> str:
        return self.arxiv.ScrollDown()
    
    def EvalGoogle(self, keywords: str) -> str:
        return self.google.Google(keywords)
    
    def EvalScrollDownGoogle(self) -> str:
        return self.google.ScrollDown()

    def EvalDuckDuckGo(self, keywords: str) -> str:
        return self.duckduckgo.DuckDuckGo(keywords)
    
    def EvalScrollDownDuckDuckGo(self) -> str:
        return self.duckduckgo.ScrollDown()
    
    def EvalBrowse(self, url: str) -> str:
        return f"BROWSE_RESULT=[{self.browser.Browse(url)}]"
    
    def EvalScrollDown(self) -> str:
        return f"SCROLLDOWN_RESULT=[{self.browser.ScrollDown()}]"
    
    def EvalBashCode(self, code: str) -> str:
        return f"SH_EXEC_RESULT=[{self.scripter.RunBash(code)}]"

    def EvalScrollUpBash(self) -> str:
        return f"SH_EXEC_RESULT=[{self.scripter.ScrollUpBash()}]"
    
    def EvalPythonCode(self, code: str) -> str:
        return f"PYTHON_EXEC_RESULT=[{self.scripter.RunPython(code)}]"
    
    def EvalScrollUpPy(self) -> str:
        return f"PYTHON_EXEC_RESULT=[{self.scripter.ScrollUpPy()}]"
    
    def EvalComplete(self, result: str):
        self.result = result
        self.prompt.Reset()
        return