from utils.AFileUtils import LoadTXTFile
from prompts.ARegex import GenerateRE4FunctionCalling

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
    
    def BuildPrompt(self):
        prompt = f"""
{self.prompt0}
"""
        #prompt += "\nConversations:"
        return self.formatter(prompt0 = prompt, conversations = self.conversations.GetConversations(frm = -4))