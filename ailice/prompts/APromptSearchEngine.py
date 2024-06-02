from importlib.resources import read_text
from ailice.common.AConfig import config
from ailice.prompts.ARegex import GenerateRE4FunctionCalling
from ailice.prompts.ATools import ConstructOptPrompt, FindRecords

class APromptSearchEngine():
    PROMPT_NAME = "search-engine"
    PROMPT_DESCRIPTION = "Searching for information using search engines on the internet or document repositories such as arXiv."
    PROMPT_PROPERTIES = {"type": "supportive"}

    def __init__(self, processor, storage, collection, conversations, formatter, outputCB = None):
        self.processor = processor
        self.storage = storage
        self.collection = collection
        self.conversations = conversations
        self.formatter = formatter
        self.outputCB = outputCB
        self.functions = []
        self.prompt0 = read_text("ailice.prompts", "prompt_searchengine.txt")
        self.PATTERNS = {"ARXIV": [{"re": GenerateRE4FunctionCalling("ARXIV<!|keywords: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SCROLL-DOWN-ARXIV": [{"re": GenerateRE4FunctionCalling("SCROLL-DOWN-ARXIV<!|session: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "GOOGLE": [{"re": GenerateRE4FunctionCalling("GOOGLE<!|keywords: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SCROLL-DOWN-GOOGLE": [{"re": GenerateRE4FunctionCalling("SCROLL-DOWN-GOOGLE<!|session: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "DUCKDUCKGO": [{"re": GenerateRE4FunctionCalling("DUCKDUCKGO<!|keywords: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SCROLL-DOWN-DUCKDUCKGO": [{"re": GenerateRE4FunctionCalling("SCROLL-DOWN-DUCKDUCKGO<!|session: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "BROWSE": [{"re": GenerateRE4FunctionCalling("BROWSE<!|url: str, session: str|!> -> str"), "isEntry": True}],
                         "SCROLL-DOWN-BROWSER": [{"re": GenerateRE4FunctionCalling("SCROLL-DOWN-BROWSER<!|session: str|!> -> str"), "isEntry": True}],
                         "SCROLL-UP-BROWSER": [{"re": GenerateRE4FunctionCalling("SCROLL-UP-BROWSER<!|session: str|!> -> str"), "isEntry": True}],
                         "SEARCH-DOWN-BROWSER": [{"re": GenerateRE4FunctionCalling("SEARCH-DOWN-BROWSER<!|query: str, session: str|!> -> str"), "isEntry": True}],
                         "SEARCH-UP-BROWSER": [{"re": GenerateRE4FunctionCalling("SEARCH-UP-BROWSER<!|query: str, session: str|!> -> str"), "isEntry": True}],
                         "GET-LINK": [{"re": GenerateRE4FunctionCalling("GET-LINK<!|text: str, session: str|!> -> str"), "isEntry": True}],
                         "RETURN": [{"re": GenerateRE4FunctionCalling("RETURN<!||!> -> str", faultTolerance = True), "isEntry": True}]}
        self.ACTIONS= {}
        return
    
    def Reset(self):
        return

    def GetPatterns(self):
        self.functions = FindRecords("Internet operations. Search engine operations. Retrieval operations.",
                                     lambda r: ((r['type']=='primary') and (r['action'] not in self.PATTERNS)),
                                     5, self.storage, self.collection + "_functions")
        context = self.conversations.GetConversations(frm = -1)[0]['msg']
        self.functions += FindRecords(context,
                                      lambda r: ((r['type']=='primary') and (r['action'] not in self.PATTERNS) and (r not in self.functions)),
                                      5, self.storage, self.collection + "_functions")
        allFunctions = sum([FindRecords("", lambda r: r['module']==m, -1, self.storage, self.collection + "_functions") for m in set([func['module'] for func in self.functions])], [])
        patterns = {f['action']: [{"re": GenerateRE4FunctionCalling(f['signature'], faultTolerance = True), "isEntry": True}] for f in allFunctions}
        patterns.update(self.PATTERNS)
        return patterns
    
    def GetActions(self):
        return self.ACTIONS
    
    def ParameterizedBuildPrompt(self, n: int):
        prompt0 = self.prompt0.replace("<FUNCTIONS>", "\n\n".join([f"#{f['prompt']}\n{f['signature']}" for f in self.functions]))
        prompt = f"""
{prompt0}

End of general instructions.

"""
        #prompt += "Conversations:"
        return self.formatter(prompt0 = prompt, conversations = self.conversations.GetConversations(frm = -n))
    
    def BuildPrompt(self):
        prompt, n = ConstructOptPrompt(self.ParameterizedBuildPrompt, low=1, high=len(self.conversations), maxLen=int(self.processor.llm.contextWindow * config.contextWindowRatio))
        if prompt is None:
            prompt, _ = self.ParameterizedBuildPrompt(1)
        return prompt

APrompt = APromptSearchEngine