from utils.AFileUtils import LoadTXTFile
from prompts.ARegex import GenerateRE4FunctionCalling

class APromptChat():
    PROMPT_NAME = "chat"

    def __init__(self, processor, storage, collection, conversations, formatter, outputCB = None):
        self.processor = processor
        self.storage = storage
        self.collection = collection
        self.conversations = conversations
        self.formatter = formatter
        self.outputCB = outputCB
        self.prompt0 = "You are a helpful assistant."
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
        return self.formatter(prompt0 = prompt, conversations = self.conversations.GetConversations(frm = 0))