from datetime import datetime
from importlib.resources import read_text
from ailice.prompts.ARegex import GenerateRE4FunctionCalling
from ailice.prompts.ATools import ConstructOptPrompt

class APromptModuleCoder():
    PROMPT_NAME = "module-coder"
    PROMPT_DESCRIPTION = "The only agent capable of building ext-modules, and this is its sole responsibility."
    PROMPT_PROPERTIES = {"type": "supportive"}

    def __init__(self, processor, storage, collection, conversations, formatter, config, outputCB = None):
        self.processor = processor
        self.storage = storage
        self.collection = collection
        self.conversations = conversations
        self.formatter = formatter
        self.config = config
        self.outputCB = outputCB
        self.prompt0 = read_text("ailice.prompts", "prompt_module_coder.txt")
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
        prompt0 = self.prompt0.replace("<CODE_EXAMPLE>", read_text("ailice.modules", "AArxiv.py"))
        prompt = f"""
{prompt0}

Current date and time(%Y-%m-%d %H:%M:%S):
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
        #prompt += "\nConversations:"
        return self.formatter(prompt0 = prompt, conversations = self.conversations.GetConversations(frm = -n))
    
    def BuildPrompt(self):
        prompt, n, tokenNum = ConstructOptPrompt(self.ParameterizedBuildPrompt, low=1, high=len(self.conversations), maxLen=int(self.processor.llm.contextWindow * self.config.contextWindowRatio))
        if prompt is None:
            prompt, tokenNum = self.ParameterizedBuildPrompt(1)
        return prompt, tokenNum
    
APrompt = APromptModuleCoder