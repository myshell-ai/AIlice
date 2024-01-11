from importlib.resources import read_text
from ailice.prompts.ARegex import GenerateRE4FunctionCalling

class APromptArticleDigest():
    PROMPT_NAME = "article-digest"
    
    def __init__(self, processor, storage, collection, conversations, formatter, outputCB = None):
        self.processor = processor
        self.storage = storage
        self.collection = collection
        self.conversations = conversations
        self.formatter = formatter
        self.outputCB = outputCB
        self.prompt0 = read_text('ailice.prompts', 'prompt_article_digest.txt')
        self.PATTERNS = {"BROWSE": [{"re": GenerateRE4FunctionCalling("BROWSE<!|url: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SCROLLDOWN": [{"re": GenerateRE4FunctionCalling("SCROLLDOWN<!||!> -> str", faultTolerance = True), "isEntry": True}],
                         "SEARCHDOWN": [{"re": GenerateRE4FunctionCalling("SEARCHDOWN<!|keyword: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SEARCHUP": [{"re": GenerateRE4FunctionCalling("SEARCHUP<!|keyword: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "Output": [{"re": r"REPORT:(?P<txt>.*?)NOTEBOOK:", "isEntry": True}],
                         "RESPOND": [{"re": GenerateRE4FunctionCalling("RESPOND<!|message: str|!> -> None", faultTolerance = True), "isEntry": True}]}
        self.ACTIONS = {"Output": {"func": self.Output}}
        return
    
    def Reset(self):
        return

    def Output(self, txt: str):
        txt = txt.strip()
        self.storage.Store(self.collection, txt)
        self.outputCB(f"OUTPUT_{self.processor.name}", txt)
        return
    
    def Recall(self, key: str):
        ret = self.storage.Query(self.collection, key, num_results=4)
        for r in ret:
            if (key not in r[0]) and (r[0] not in key):
                return r[0]
        return "None."
    
    def GetPatterns(self):
        return self.PATTERNS
    
    def GetActions(self):
        return self.ACTIONS

    def BuildPrompt(self):
        context = self.conversations.GetConversations(frm = -1)[0]['msg']
        prompt = f"""
{self.prompt0}

End of general instructions.

RELEVANT INFORMATION: {self.Recall(context).strip()}

"""
        #print(prompt)
        return self.formatter(prompt0 = prompt, conversations = self.conversations.GetConversations(frm = -2))
    