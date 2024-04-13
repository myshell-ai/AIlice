from importlib.resources import read_text
from ailice.common.AConfig import config
from ailice.prompts.ARegex import GenerateRE4FunctionCalling
from ailice.prompts.ATools import ConstructOptPrompt, FindRelatedRecords

class APromptSearchEngine():
    PROMPT_NAME = "search-engine"
    PROMPT_DESCRIPTION = "Searching for information using search engines on the internet or document repositories such as arXiv."

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
                         "SCROLL_DOWN_ARXIV": [{"re": GenerateRE4FunctionCalling("SCROLL_DOWN_ARXIV<!|session: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "GOOGLE": [{"re": GenerateRE4FunctionCalling("GOOGLE<!|keywords: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SCROLL_DOWN_GOOGLE": [{"re": GenerateRE4FunctionCalling("SCROLL_DOWN_GOOGLE<!|session: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "DUCKDUCKGO": [{"re": GenerateRE4FunctionCalling("DUCKDUCKGO<!|keywords: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SCROLL_DOWN_DUCKDUCKGO": [{"re": GenerateRE4FunctionCalling("SCROLL_DOWN_DUCKDUCKGO<!|session: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "BROWSE": [{"re": GenerateRE4FunctionCalling("BROWSE<!|url: str, session: str|!> -> str"), "isEntry": True}],
                         "SCROLL_DOWN_BROWSER": [{"re": GenerateRE4FunctionCalling("SCROLL_DOWN_BROWSER<!|session: str|!> -> str"), "isEntry": True}],
                         "SCROLL_UP_BROWSER": [{"re": GenerateRE4FunctionCalling("SCROLL_UP_BROWSER<!|session: str|!> -> str"), "isEntry": True}],
                         "SEARCH_DOWN_BROWSER": [{"re": GenerateRE4FunctionCalling("SEARCH_DOWN_BROWSER<!|query: str, session: str|!> -> str"), "isEntry": True}],
                         "SEARCH_UP_BROWSER": [{"re": GenerateRE4FunctionCalling("SEARCH_UP_BROWSER<!|query: str, session: str|!> -> str"), "isEntry": True}],
                         "GET_LINK": [{"re": GenerateRE4FunctionCalling("GET_LINK<!|text: str, session: str|!> -> str"), "isEntry": True}],
                         "RESPOND": [{"re": GenerateRE4FunctionCalling("RESPOND<!|message: str|!> -> None", faultTolerance = True), "isEntry": True}]}
        self.ACTIONS= {}
        return
    
    def Reset(self):
        return
    
    def GetPatterns(self):
        functions = FindRelatedRecords("Internet operations. Search engine operations. Retrieval operations.", len(self.PATTERNS) + 10, self.storage, self.collection + "_functions")
        self.functions = [f for f in functions if f['action'] not in self.PATTERNS]
        patterns = {f['action']: [{"re": GenerateRE4FunctionCalling(f['signature'], faultTolerance = True), "isEntry": True}] for f in self.functions}
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
        ret = self.formatter(prompt0 = prompt, conversations = self.conversations.GetConversations(frm = -n))
        return ret, self.formatter.Len(ret)
    
    def BuildPrompt(self):
        prompt, n = ConstructOptPrompt(self.ParameterizedBuildPrompt, low=1, high=len(self.conversations), maxLen=int(self.processor.llm.contextWindow * config.contextWindowRatio))
        if prompt is None:
            prompt, _ = self.ParameterizedBuildPrompt(1)
        return prompt

APrompt = APromptSearchEngine