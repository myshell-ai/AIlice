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
        self.PATTERNS = {"CALL": [{"re": GenerateRE4FunctionCalling("CALL<!|program: str, target: str, msg: str|!> -> str"), "isEntry": True}],
                         "RESPOND": [{"re": GenerateRE4FunctionCalling("RESPOND<!|message: str|!> -> None", faultTolerance = True), "isEntry": True}],
                         "BASH": [{"re": GenerateRE4FunctionCalling("BASH<!|code: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "PYTHON": [{"re": GenerateRE4FunctionCalling("PYTHON<!|code: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "UpdateMemory": [{"re": r"UPDATED MEMORY(?P<newState>.*?)", "isEntry": True}]}
        self.ACTIONS= {"UpdateMemory": {"func": self.UpdateMemory}}
        self.memory = ""
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
    
    def BuildPrompt(self):
        prompt = f"""
{self.prompt0}

End of general instructions.

Active Agents: {[k+": program "+p.GetPromptName() for k,p in self.processor.subProcessors.items()]}
"""
        #prompt += "\nConversations:"
        return self.formatter(prompt0 = prompt, conversations = self.conversations.GetConversations(frm = -4))