from importlib.resources import read_text
from ailice.common.AConfig import config
from ailice.common.utils.ATextSpliter import paragraph_generator
from ailice.prompts.ARegex import GenerateRE4FunctionCalling, VAR_DEF
from ailice.prompts.ATools import ConstructOptPrompt

class APromptArticleDigest():
    PROMPT_NAME = "article-digest"
    
    def __init__(self, processor, storage, collection, conversations, formatter, outputCB = None):
        self.processor = processor
        self.storage = storage
        self.collection = f"{collection}_{self.processor.name}_article"
        self.conversations = conversations
        self.formatter = formatter
        self.outputCB = outputCB
        self.prompt0 = read_text('ailice.prompts', 'prompt_article_digest.txt')
        self.PATTERNS = {"READ": [{"re": GenerateRE4FunctionCalling("READ<!|url: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SCROLLDOWN": [{"re": GenerateRE4FunctionCalling("SCROLLDOWN<!||!> -> str", faultTolerance = True), "isEntry": True}],
                         "SEARCHDOWN": [{"re": GenerateRE4FunctionCalling("SEARCHDOWN<!|query: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SEARCHUP": [{"re": GenerateRE4FunctionCalling("SEARCHUP<!|query: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "RETRIEVE": [{"re": GenerateRE4FunctionCalling("RETRIEVE<!|keywords: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "RESPOND": [{"re": GenerateRE4FunctionCalling("RESPOND<!|message: str|!> -> None", faultTolerance = True), "isEntry": True}],
                         "VAR": [{"re": VAR_DEF, "isEntry": True}],
                         "PRINT": [{"re": GenerateRE4FunctionCalling("PRINT<!|varName: str|!> -> str", faultTolerance = True), "isEntry": True}]}
        self.ACTIONS = {"READ": {"func": self.Read},
                        "RETRIEVE": {"func": self.Recall}}
        return
    
    def Reset(self):
        return

    def Read(self, url: str) -> str:
        ret = self.processor.modules['browser']['module'].Browse(url)
        fulltxt = self.processor.modules['browser']['module'].GetFullText(url)
        for txt in paragraph_generator(fulltxt):
            self.storage.Store(self.collection, txt)
        return ret
    
    def Recall(self, keywords: str) -> str:
        ret = self.storage.Query(self.collection, keywords, num_results=1)
        if 0 != len(ret):
            return ret[0][0]
        else:
            return "None."
    
    def GetPatterns(self):
        return self.PATTERNS
    
    def GetActions(self):
        return self.ACTIONS
    
    def ParameterizedBuildPrompt(self, n: int):
        context = self.conversations.GetConversations(frm = -1)[0]['msg']
        prompt = f"""
{self.prompt0}

End of general instructions.

RELEVANT INFORMATION: {self.Recall(context).strip()}

"""
        #print(prompt)
        ret = self.formatter(prompt0 = prompt, conversations = self.conversations.GetConversations(frm = -n))
        return ret, self.formatter.Len(ret)
    
    def BuildPrompt(self):
        prompt, n = ConstructOptPrompt(self.ParameterizedBuildPrompt, low=1, high=len(self.conversations), maxLen=int(self.processor.llm.contextWindow * config.contextWindowRatio))
        if prompt is None:
            prompt, _ = self.ParameterizedBuildPrompt(1)
        return prompt