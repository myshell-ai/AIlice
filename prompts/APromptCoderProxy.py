from utils.AFileUtils import LoadTXTFile
from prompts.ARegex import GenerateRE4FunctionCalling

class APromptCoderProxy():
    PROMPT_NAME = "coder-proxy"

    def __init__(self, processor, storage, collection, conversations, formatter, outputCB = None):
        self.processor = processor
        self.storage = storage
        self.collection = collection
        self.conversations = conversations
        self.formatter = formatter
        self.formatter.systemAsUser = False
        self.outputCB = outputCB
        self.prompt0 = LoadTXTFile("prompts/prompt_coderproxy.txt")
        self.PATTERNS = {"CALL": [{"re": GenerateRE4FunctionCalling("CALL<!|agentType: str, agentName: str, msg: str|!> -> str"), "isEntry": True}],
                         "RESPOND": [{"re": GenerateRE4FunctionCalling("RESPOND<!|message: str|!> -> None", faultTolerance = True), "isEntry": True}],
                         "BASH": [{"re": GenerateRE4FunctionCalling("BASH<!|code: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "PYTHON": [{"re": GenerateRE4FunctionCalling("PYTHON<!|code: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "UpdateMemory": [{"re": r"UPDATED MEMORY(?P<newState>.*?)", "isEntry": True}],
                         "SetVar": [{"re": r"(?P<varName>[a-zA-Z0-9_-]+)[ ]*=[ ]*<!\|(?P<varValue>.*?)\|!>", "isEntry": True}],
                         "GetVar": [{"re": r"\$(?P<varName>[a-zA-Z0-9_-]+)", "isEntry": False}],
                         "PrintVar": [{"re": GenerateRE4FunctionCalling("PRINT<!|varName: str|!> -> str", faultTolerance = True), "isEntry": True}]}
        self.ACTIONS= {"UpdateMemory": {"func": self.UpdateMemory},
                       "SetVar": {"func": self.SetVar},
                       "GetVar": {"func": self.GetVar},
                       "PrintVar": {"func": self.GetVar}}
        self.memory = ""
        self.vars = {}
        return
    
    def Reset(self):
        return
    
    def GetPatterns(self):
        return self.PATTERNS
    
    def GetActions(self):
        return self.ACTIONS
    
    def UpdateMemory(self, newMemory: str):
        self.memory = newMemory
        return
    
    def SetVar(self, varName: str, varValue: str):
        self.vars[varName] = varValue
        return
    
    def GetVar(self, varName: str) -> str:
        return self.vars.get(varName, "")
    
    def BuildPrompt(self):
        prompt = f"""
{self.prompt0}

End of general instructions.

Active Agents: {[k+": agentType "+p.GetPromptName() for k,p in self.processor.subProcessors.items()]}
Variables: {[k for k in self.vars]}
"""
        #prompt += "\nConversations:"
        return self.formatter(prompt0 = prompt, conversations = self.conversations.GetConversations(frm = -4))