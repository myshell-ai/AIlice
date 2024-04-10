from importlib.resources import read_text
from ailice.common.AConfig import config
from ailice.prompts.ARegex import GenerateRE4FunctionCalling
from ailice.prompts.ATools import ConstructOptPrompt


class APromptModuleLoader():
    PROMPT_NAME = "module-loader"

    def __init__(self, processor, storage, collection, conversations, formatter, outputCB = None):
        self.processor = processor
        self.storage = storage
        self.collection = collection
        self.conversations = conversations
        self.formatter = formatter
        self.outputCB = outputCB
        self.prompt0 = read_text("ailice.prompts", "prompt_module_loader.txt")
        self.memory = ""
        self.PATTERNS = {"LOADMODULE": [{"re": GenerateRE4FunctionCalling("LOADMODULE<!|addr: str|!> -> str", faultTolerance = True), "isEntry": True}]}
        self.ACTIONS= {"LOADMODULE": {"func": self.LoadModule}}
        return
    
    def Reset(self):
        return
    
    def GetPatterns(self):
        return self.PATTERNS
    
    def GetActions(self):
        return self.ACTIONS
    
    def LoadModule(self, addr: str) -> str:
        try:
            ret = self.processor.RegisterModules([addr])
            prompts = []
            for r in ret:
                self.processor.interpreter.RegisterPattern(nodeType=r['action'], pattern=GenerateRE4FunctionCalling(r['signature'], faultTolerance = True), isEntry=True)
                prompts.append(f"{r['signature']}: {r['prompt']}")
            self.memory = "\n".join(prompts)
            ret = self.memory
        except Exception as e:
            ret = f"Exception: {str(e)}"
        return ret
    
    def ParameterizedBuildPrompt(self, n: int):
        prompt = f"""
{self.prompt0}

Variables:
{self.processor.EnvSummary()}

MODULE DETAILS:
{self.memory}

"""
        #prompt += "\nConversations:"
        ret = self.formatter(prompt0 = prompt, conversations = self.conversations.GetConversations(frm = -n))
        return ret, self.formatter.Len(ret)
    
    def BuildPrompt(self):
        prompt, n = ConstructOptPrompt(self.ParameterizedBuildPrompt, low=1, high=len(self.conversations), maxLen=int(self.processor.llm.contextWindow * config.contextWindowRatio))
        if prompt is None:
            prompt, _ = self.ParameterizedBuildPrompt(1)
        return prompt