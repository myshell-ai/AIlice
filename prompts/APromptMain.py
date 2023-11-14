from utils.AFileUtils import LoadTXTFile
from prompts.ARegex import GenerateRE4FunctionCalling

class APromptMain():
    PROMPT_NAME = "main"

    def __init__(self, processor, storage, collection, conversations, formatter, outputCB = None):
        self.processor = processor
        self.storage = storage
        self.collection = collection
        self.conversations = conversations
        self.formatter = formatter
        self.outputCB = outputCB
        self.prompt0 = LoadTXTFile("prompts/prompt_simple.txt")
        self.PATTERNS = {"CALL": [{"re": GenerateRE4FunctionCalling("CALL<!|agentType: str, agentName: str, msg: str|!> -> str"), "isEntry": True}]}
        self.ACTIONS= {}
        return
    
    def Recall(self, key: str):
        ret = self.storage.Query(self.collection, key)
        if (0 != len(ret)) and (ret[0][1] <= 0.5):
            return ret[0][0]
        else:
            return "None."
    
    def Reset(self):
        return
    
    def GetPatterns(self):
        return self.PATTERNS
    
    def GetActions(self):
        return self.ACTIONS
    
    def BuildPrompt(self):
        context = str(self.formatter(prompt0 = "", conversations = self.conversations.GetConversations(frm = -1), encode = False))
        prompt = f"""
{self.prompt0}

End of general instructions.

Active Agents: {[k+": agentType "+p.GetPromptName() for k,p in self.processor.subProcessors.items()]}
Relevant Information:
{self.Recall(context)}
"""
        #prompt += "\nConversations:"
        return self.formatter(prompt0 = prompt, conversations = self.conversations.GetConversations(frm = -4))