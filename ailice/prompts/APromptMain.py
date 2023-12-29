from ailice.common.AConfig import config
from ailice.common.utils.AFileUtils import LoadTXTFile
from ailice.prompts.ARegex import GenerateRE4FunctionCalling
from ailice.prompts.ATools import ConstructOptPrompt

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
    
    def ParameterizedBuildPrompt(self, n: int):
        context = str(self.formatter(prompt0 = "", conversations = self.conversations.GetConversations(frm = -1), encode = False))
        prompt = f"""
{self.prompt0}

End of general instructions.

Active Agents: {[k+": agentType "+p.GetPromptName() for k,p in self.processor.subProcessors.items()]}
Relevant Information:
{self.Recall(context)}
"""
        #prompt += "\nConversations:"
        ret = self.formatter(prompt0 = prompt, conversations = self.conversations.GetConversations(frm = -n))
        return ret, self.formatter.Len(ret)
    
    def BuildPrompt(self):
        prompt, n = ConstructOptPrompt(self.ParameterizedBuildPrompt, low=1, high=len(self.conversations), maxLen=int(self.processor.llm.contextWindow * config.contextWindowRatio))
        if prompt is None:
            prompt = self.ParameterizedBuildPrompt(1)
        return prompt