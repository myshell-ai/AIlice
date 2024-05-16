from importlib.resources import read_text
from ailice.common.AConfig import config
from ailice.prompts.ARegex import GenerateRE4FunctionCalling
from ailice.prompts.ATools import ConstructOptPrompt, FindRecords


class APromptResearcher():
    PROMPT_NAME = "researcher"
    PROMPT_DESCRIPTION = "Conduct an internet investigation on a particular topic or gather data. It also has the capability to execute simple scripts."
    PROMPT_PROPERTIES = {"type": "primary"}
    
    def __init__(self, processor, storage, collection, conversations, formatter, outputCB = None):
        self.processor = processor
        self.storage = storage
        self.collection = collection
        self.conversations = conversations
        self.formatter = formatter
        self.outputCB = outputCB
        self.functions = []
        self.prompt0 = read_text("ailice.prompts", "prompt_researcher.txt")
        self.PATTERNS = {"CALL": [{"re": GenerateRE4FunctionCalling("CALL<!|agentType: str, agentName: str, msg: str|!> -> str"), "isEntry": True}],
                         "RESPOND": [{"re": GenerateRE4FunctionCalling("RESPOND<!|message: str|!> -> None", faultTolerance = True), "isEntry": True}],
                         "BROWSE": [{"re": GenerateRE4FunctionCalling("BROWSE<!|url: str, session: str|!> -> str"), "isEntry": True}],
                         "SCROLL_DOWN_BROWSER": [{"re": GenerateRE4FunctionCalling("SCROLL_DOWN_BROWSER<!|session: str|!> -> str"), "isEntry": True}],
                         "SCROLL_UP_BROWSER": [{"re": GenerateRE4FunctionCalling("SCROLL_UP_BROWSER<!|session: str|!> -> str"), "isEntry": True}],
                         "SEARCH_DOWN_BROWSER": [{"re": GenerateRE4FunctionCalling("SEARCH_DOWN_BROWSER<!|query: str, session: str|!> -> str"), "isEntry": True}],
                         "SEARCH_UP_BROWSER": [{"re": GenerateRE4FunctionCalling("SEARCH_UP_BROWSER<!|query: str, session: str|!> -> str"), "isEntry": True}],
                         "GET_LINK": [{"re": GenerateRE4FunctionCalling("GET_LINK<!|text: str, session: str|!> -> str"), "isEntry": True}],
                         "SCREENSHOT": [{"re": GenerateRE4FunctionCalling("SCREENSHOT<!||!> -> AImage"), "isEntry": True}],
                         "READ_IMAGE": [{"re": GenerateRE4FunctionCalling("READ_IMAGE<!|path: str|!> -> AImage", faultTolerance = True), "isEntry": True}],
                         "WRITE_IMAGE": [{"re": GenerateRE4FunctionCalling("WRITE_IMAGE<!|image: AImage, path: str|!>"), "isEntry": True}],
                         "BASH": [{"re": GenerateRE4FunctionCalling("BASH<!|code: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "PYTHON": [{"re": GenerateRE4FunctionCalling("PYTHON<!|code: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "CHECK_OUTPUT": [{"re": GenerateRE4FunctionCalling("CHECK_OUTPUT<!|session: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SCROLL_UP_TERM": [{"re": GenerateRE4FunctionCalling("SCROLL_UP_TERM<!|session: str|!> -> str"), "isEntry": True}],
                         "WAIT": [{"re": GenerateRE4FunctionCalling("WAIT<!|duration: int|!> -> str"), "isEntry": True}],
                         "STORE": [{"re": GenerateRE4FunctionCalling("STORE<!|txt: str|!> -> None", faultTolerance = True), "isEntry": True}],
                         "QUERY": [{"re": GenerateRE4FunctionCalling("QUERY<!|keywords: str|!> -> str", faultTolerance = True), "isEntry": True}]}
        self.ACTIONS = {}
        return
    
    def Recall(self, key: str):
        ret = self.storage.Query(collection=self.collection, clue=key, num_results=4)
        for r in ret:
            if (key not in r[0]) and (r[0] not in key):
                return r[0]
        return "None."

    def GetPatterns(self):
        self.functions = FindRecords("Internet operations, file operations.",
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
        context = self.conversations.GetConversations(frm = -1)[0]['msg']
        prompt0 = self.prompt0.replace("<FUNCTIONS>", "\n\n".join([f"#{f['prompt']}\n{f['signature']}" for f in self.functions]))
        agents = FindRecords("academic, mathematics, search, investigation, analysis, logic.", lambda r: (r['properties']['type'] == 'primary'), 10, self.storage, self.collection + "_prompts")
        agents += FindRecords(context, lambda r: (r['properties']['type'] == 'primary') and (r not in agents), 5, self.storage, self.collection + "_prompts")
        prompt0 = prompt0.replace("<AGENTS>", "\n".join([f" - {agent['name']}: {agent['desc']}" for agent in agents if agent['name'] not in ["researcher", "search-engine", "article-digest", "coder-proxy"]]))

        prompt = f"""
{prompt0}

End of general instructions.

Active Agents: {[k+": agentType "+p.GetPromptName() for k,p in self.processor.subProcessors.items()]}

Variables:
{self.processor.EnvSummary()}

Task Objective:
{self.processor.interpreter.env.get('task_objective', 'Not set.')}

Relevant Information: {self.Recall(context).strip()}
The "RELEVANT INFORMATION" part contains data that may be related to the current task, originating from your own history or the histories of other agents. Please refrain from attempting to invoke functions mentioned in the relevant information, as you may not necessarily have the permissions to do so.

"""
        #print(prompt)
        ret = self.formatter(prompt0 = prompt, conversations = self.conversations.GetConversations(frm = -n))
        return ret, self.formatter.Len(ret)
    
    def BuildPrompt(self):
        prompt, n = ConstructOptPrompt(self.ParameterizedBuildPrompt, low=1, high=len(self.conversations), maxLen=int(self.processor.llm.contextWindow * config.contextWindowRatio))
        if prompt is None:
            prompt, _ = self.ParameterizedBuildPrompt(1)
        return prompt
    
APrompt = APromptResearcher