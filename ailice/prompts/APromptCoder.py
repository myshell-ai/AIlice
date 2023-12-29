from common.AConfig import config
from common.utils.AFileUtils import LoadTXTFile
from prompts.ARegex import GenerateRE4FunctionCalling
from prompts.ATools import ConstructOptPrompt

class APromptCoder():
    PROMPT_NAME = "coder"

    def __init__(self, processor, storage, collection, conversations, formatter, outputCB = None):
        self.processor = processor
        self.storage = storage
        self.collection = collection
        self.conversations = conversations
        self.formatter = formatter
        self.outputCB = outputCB
        self.prompt0 = LoadTXTFile("prompts/prompt_coder.txt")
        self.PATTERNS = {}
        self.ACTIONS= {}

        return
    
    def Reset(self):
        return
    
    def GetPatterns(self):
        return self.PATTERNS
    
    def GetActions(self):
        return self.ACTIONS
    
    def ParameterizedBuildPrompt(self, n: int):
        prompt = f"""
{self.prompt0}
"""
        #prompt += "\nConversations:"
        ret = self.formatter(prompt0 = prompt, conversations = self.conversations.GetConversations(frm = -n))
        return ret, self.formatter.Len(ret)
    
    def BuildPrompt(self):
        prompt, n = ConstructOptPrompt(self.ParameterizedBuildPrompt, low=1, high=len(self.conversations), maxLen=int(self.processor.llm.contextWindow * config.contextWindowRatio))
        if prompt is None:
            prompt = self.ParameterizedBuildPrompt(1)
        return prompt