import random
from importlib.resources import read_text
from ailice.common.AConfig import config
from ailice.common.utils.ATextSpliter import paragraph_generator
from ailice.prompts.ARegex import GenerateRE4FunctionCalling
from ailice.prompts.ATools import ConstructOptPrompt

class APromptArticleDigest():
    PROMPT_NAME = "article-digest"
    PROMPT_DESCRIPTION = "Literature reading comprehension and related question answering. You need to include the URL or file path of the target documentation in the request message."
    PROMPT_PROPERTIES = {"type": "primary"}
    
    def __init__(self, processor, storage, collection, conversations, formatter, outputCB = None):
        self.processor = processor
        self.storage = storage
        self.collection = f"{collection}_{self.processor.name}_article"
        self.conversations = conversations
        self.formatter = formatter
        self.outputCB = outputCB
        self.prompt0 = read_text('ailice.prompts', 'prompt_article_digest.txt')
        self.PATTERNS = {"READ": [{"re": GenerateRE4FunctionCalling("READ<!|url: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SCROLL-DOWN-BROWSER": [{"re": GenerateRE4FunctionCalling("SCROLL-DOWN-BROWSER<!|session: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SCROLL-UP-BROWSER": [{"re": GenerateRE4FunctionCalling("SCROLL-UP-BROWSER<!|session: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SEARCH-DOWN-BROWSER": [{"re": GenerateRE4FunctionCalling("SEARCH-DOWN-BROWSER<!|query: str, session: str|!> -> str"), "isEntry": True}],
                         "SEARCH-UP-BROWSER": [{"re": GenerateRE4FunctionCalling("SEARCH-UP-BROWSER<!|query: str, session: str|!> -> str"), "isEntry": True}],
                         "GET-LINK": [{"re": GenerateRE4FunctionCalling("GET-LINK<!|text: str, session: str|!> -> str"), "isEntry": True}],
                         "RETRIEVE": [{"re": GenerateRE4FunctionCalling("RETRIEVE<!|keywords: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "RESPOND": [{"re": GenerateRE4FunctionCalling("RESPOND<!|message: str|!> -> None", faultTolerance = True), "isEntry": True}],
                        }
        self.ACTIONS = {"READ": {"func": self.Read},
                        "RETRIEVE": {"func": self.Recall}}
        return
    
    def Reset(self):
        return

    def Read(self, url: str) -> str:
        session = f"webpage_{random.randint(0,99999999)}"
        ret = self.processor.modules['browser']['module'].Browse(url, session)
        fulltxt = self.processor.modules['browser']['module'].GetFullText(session)
        for txt in paragraph_generator(fulltxt):
            self.storage.Store(self.collection, txt)
        return ret
    
    def Recall(self, keywords: str) -> str:
        ret = self.storage.Query(collection=self.collection, clue=keywords, num_results=1)
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

Variables:
{self.processor.EnvSummary()}

Task Objective:
{self.processor.interpreter.env.get('task_objective', 'Not set.')}

RELEVANT INFORMATION: {self.Recall(context).strip()}

"""
        #print(prompt)
        return self.formatter(prompt0 = prompt, conversations = self.conversations.GetConversations(frm = -n))
    
    def BuildPrompt(self):
        prompt, n = ConstructOptPrompt(self.ParameterizedBuildPrompt, low=1, high=len(self.conversations), maxLen=int(self.processor.llm.contextWindow * config.contextWindowRatio))
        if prompt is None:
            prompt, _ = self.ParameterizedBuildPrompt(1)
        return prompt

APrompt = APromptArticleDigest