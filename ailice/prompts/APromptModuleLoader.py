import sys
import string
import secrets
import importlib
from importlib.resources import read_text
from ailice.common.AConfig import config
from ailice.common.APrompts import promptsManager
from ailice.prompts.ARegex import GenerateRE4FunctionCalling
from ailice.prompts.ATools import ConstructOptPrompt

def GenSym(length=32, prefix="APrompt_"):
    alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits
    symbol = "".join([secrets.choice(alphabet) for i in range(length)])
    return prefix + symbol

class APromptModuleLoader():
    PROMPT_NAME = "module-loader"
    PROMPT_DESCRIPTION = "An agent that can help you load and use extensions such as ext-modules and ext-prompts. You need to include the address of the ext-module / path to ext-prompt in your request message. You can let it help you interact with the ext-module. You can use this agent to assist in ext-module debugging."

    def __init__(self, processor, storage, collection, conversations, formatter, outputCB = None):
        self.processor = processor
        self.storage = storage
        self.collection = collection
        self.conversations = conversations
        self.formatter = formatter
        self.outputCB = outputCB
        self.prompt0 = read_text("ailice.prompts", "prompt_module_loader.txt")
        self.memory = ""
        self.PATTERNS = {"LOADEXTMODULE": [{"re": GenerateRE4FunctionCalling("LOADEXTMODULE<!|addr: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "LOADEXTPROMPT": [{"re": GenerateRE4FunctionCalling("LOADEXTPROMPT<!|path: str|!> -> str", faultTolerance = True), "isEntry": True}]}
        self.ACTIONS= {"LOADEXTMODULE": {"func": self.LoadExtModule},
                       "LOADEXTPROMPT": {"func": self.LoadExtPrompt}}
        return
    
    def Reset(self):
        return
    
    def GetPatterns(self):
        return self.PATTERNS
    
    def GetActions(self):
        return self.ACTIONS
    
    def LoadExtModule(self, addr: str) -> str:
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
    
    def LoadExtPrompt(self, path: str) -> str:
        ret = ""
        try:
            moduleName = GenSym()
            spec = importlib.util.spec_from_file_location(moduleName, path)
            promptModule = importlib.util.module_from_spec(spec)
            sys.modules[moduleName] = promptModule
            spec.loader.exec_module(promptModule)
            
            ret += promptsManager.RegisterPrompt(promptModule.APrompt)
            if "" == ret:
                ret += f"Prompt module {promptModule.APrompt.PROMPT_NAME} has been loaded. Its description information is as follows:\n{promptModule.APrompt.PROMPT_DESCRIPTION}"
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
    
APrompt = APromptModuleLoader