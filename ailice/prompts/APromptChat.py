from datetime import datetime
from ailice.common.AConfig import config
from ailice.common.utils.AFileUtils import LoadTXTFile
from ailice.prompts.ARegex import GenerateRE4FunctionCalling
from ailice.prompts.ATools import ConstructOptPrompt


class APromptChat():
    PROMPT_NAME = "chat"
    PROMPT_DESCRIPTION = "A chatbot with no capability for external interactions."
    PROMPT_PROPERTIES = {"type": "primary"}

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
    
    def ParameterizedBuildPrompt(self, n: int):
        prompt = f"""
{self.prompt0}

Current date and time(%Y-%m-%d %H:%M:%S):
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
        #prompt += "\nConversations:"
        return self.formatter(prompt0 = prompt, conversations = self.conversations.GetConversations(frm = -n))
    
    def BuildPrompt(self):
        prompt, n = ConstructOptPrompt(self.ParameterizedBuildPrompt, low=1, high=len(self.conversations), maxLen=int(self.processor.llm.contextWindow * config.contextWindowRatio))
        if prompt is None:
            prompt, _ = self.ParameterizedBuildPrompt(1)
        return prompt
    
APrompt = APromptChat
