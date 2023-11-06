from utils.AFileUtils import LoadTXTFile
from prompts.ARegex import GenerateRE4FunctionCalling

class APromptArticleDigest():
    PROMPT_NAME = "article-digest"
    
    def __init__(self, processor, storage, collection, conversations, formatter, outputCB = None):
        self.processor = processor
        self.storage = storage
        self.collection = collection
        self.conversations = conversations
        self.formatter = formatter
        self.outputCB = outputCB
        self.prompt0 = LoadTXTFile("prompts/prompt_article_digest.txt")
        self.PATTERNS = {"BROWSE": [{"re": GenerateRE4FunctionCalling("BROWSE<!|url: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SCROLLDOWN": [{"re": GenerateRE4FunctionCalling("SCROLLDOWN<!||!> -> str", faultTolerance = True), "isEntry": True}],
                         "Output": [{"re": r"REPORT:(?P<txt>.*?)NOTEBOOK:", "isEntry": True}],
                         "RESPOND": [{"re": GenerateRE4FunctionCalling("RESPOND<!|message: str|!> -> None", faultTolerance = True), "isEntry": True}]}
        self.ACTIONS = {"Output": {"func": self.Output}}
        return
    
    def Reset(self):
        return

    def Output(self, txt: str):
        txt = txt.strip()
        self.storage.Store(self.collection, txt)
        self.outputCB("OUTPUT", txt)
        return
    
    def Recall(self, key: str):
        ret = self.storage.Query(self.collection, key)
        if (0 != len(ret)): #and (ret[0][1] <= 0.5):
            return ret[0][0]
        else:
            return "None."
    
    def GetPatterns(self):
        return self.PATTERNS
    
    def GetActions(self):
        return self.ACTIONS

    def BuildPrompt(self):
        context = str(self.formatter(prompt0 = "", conversations = self.conversations.GetConversations(frm = -1), encode = False))
        prompt = f"""
{self.prompt0}

End of general instructions.

RELEVANT INFORMATION: {self.Recall(context).strip()}

"""
        #print(prompt)
        return self.formatter(prompt0 = prompt, conversations = self.conversations.GetConversations(frm = -2))
    