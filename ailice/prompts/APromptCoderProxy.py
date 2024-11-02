from importlib.resources import read_text
from ailice.common.AConfig import config
from ailice.prompts.ARegex import GenerateRE4FunctionCalling
from ailice.prompts.ATools import ConstructOptPrompt, FindRecords

class APromptCoderProxy():
    PROMPT_NAME = "coder-proxy"
    PROMPT_DESCRIPTION = "They are adept at using programming to solve problems and has execution permissions for both Bash and Python."
    PROMPT_PROPERTIES = {"type": "primary"}

    def __init__(self, processor, storage, collection, conversations, formatter, outputCB = None):
        self.processor = processor
        self.storage = storage
        self.collection = collection
        self.conversations = conversations
        self.formatter = formatter
        self.outputCB = outputCB
        self.functions = []
        self.prompt0 = read_text("ailice.prompts", "prompt_coderproxy.txt")
        self.PATTERNS = {"CALL": [{"re": GenerateRE4FunctionCalling("CALL<!|agentType: str, agentName: str, msg: str|!> -> str"), "isEntry": True}],
                         "RESPOND": [{"re": GenerateRE4FunctionCalling("RESPOND<!|message: str|!> -> None", faultTolerance = True), "isEntry": True}],
                         "DEFINE-CODE-VARS": [{"re": GenerateRE4FunctionCalling("DEFINE-CODE-VARS<!||!> -> str"), "isEntry": True}],
                         "SAVE-TO-FILE": [{"re": GenerateRE4FunctionCalling("SAVE-TO-FILE<!|filePath: str, code: str|!> -> str"), "isEntry": True}],
                         "BROWSE-EDIT": [{"re": GenerateRE4FunctionCalling("BROWSE-EDIT<!|path: str, session: str|!> -> str"), "isEntry": True}],
                         "SCROLL-DOWN-BROWSER": [{"re": GenerateRE4FunctionCalling("SCROLL-DOWN-BROWSER<!|session: str|!> -> str"), "isEntry": True}],
                         "SCROLL-UP-BROWSER": [{"re": GenerateRE4FunctionCalling("SCROLL-UP-BROWSER<!|session: str|!> -> str"), "isEntry": True}],
                         "SEARCH-DOWN-BROWSER": [{"re": GenerateRE4FunctionCalling("SEARCH-DOWN-BROWSER<!|query: str, session: str|!> -> str"), "isEntry": True}],
                         "SEARCH-UP-BROWSER": [{"re": GenerateRE4FunctionCalling("SEARCH-UP-BROWSER<!|query: str, session: str|!> -> str"), "isEntry": True}],
                         "REPLACE": [{"re": GenerateRE4FunctionCalling("REPLACE<!|pattern: str, replacement: str, regexMode: bool, session: str|!> -> str"), "isEntry": True}],
                         "SAVETO": [{"re": GenerateRE4FunctionCalling("SAVETO<!|dstPath: str, session: str|!> -> str"), "isEntry": True}],
                         "SCREENSHOT": [{"re": GenerateRE4FunctionCalling("SCREENSHOT<!||!> -> AImage"), "isEntry": True}],
                         "READ-IMAGE": [{"re": GenerateRE4FunctionCalling("READ-IMAGE<!|path: str|!> -> AImage", faultTolerance=True), "isEntry": True}],
                         "WRITE-IMAGE": [{"re": GenerateRE4FunctionCalling("WRITE-IMAGE<!|image: AImage, path: str|!> -> str"), "isEntry": True}],
                         "BASH": [{"re": GenerateRE4FunctionCalling("BASH<!|code: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "PYTHON": [{"re": GenerateRE4FunctionCalling("PYTHON<!|code: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "CHECK-OUTPUT": [{"re": GenerateRE4FunctionCalling("CHECK-OUTPUT<!|session: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SCROLL-UP-TERM": [{"re": GenerateRE4FunctionCalling("SCROLL-UP-TERM<!|session: str|!> -> str"), "isEntry": True}],
                         "WAIT": [{"re": GenerateRE4FunctionCalling("WAIT<!|duration: int|!> -> str"), "isEntry": True}],
                         "LOADEXTMODULE": [{"re": GenerateRE4FunctionCalling("LOADEXTMODULE<!|addr: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "LOADEXTPROMPT": [{"re": GenerateRE4FunctionCalling("LOADEXTPROMPT<!|path: str|!> -> str", faultTolerance = True), "isEntry": True}]}
        self.ACTIONS= {}
        return
    
    def Reset(self):
        return
    
    def GetPatterns(self):
        self.functions = FindRecords("programming, debugging, file operation, system operation.",
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
    
    def Recall(self, key: str):
        ret = self.storage.Recall(collection=self.collection, query=key, num_results=4)
        for r in ret:
            if (key not in r[0]) and (r[0] not in key):
                return r[0]
        return "None."
    
    def ParameterizedBuildPrompt(self, n: int):
        self.platformInfo = self.processor.modules['scripter']['module'].PlatformInfo() if not hasattr(self, 'platformInfo') else self.platformInfo
        context = self.conversations.GetConversations(frm = -1)[0]['msg']
        prompt0 = self.prompt0.replace("<FUNCTIONS>", "\n\n".join([f"#{f['prompt']}\n{f['signature']}" for f in self.functions]))
        agents = FindRecords("Programming, debugging, investigating, searching, files, systems.", lambda r: (r['properties']['type'] == 'primary'), 5, self.storage, self.collection + "_prompts")
        agents += FindRecords(context, lambda r: (r['properties']['type'] == 'primary') and (r not in agents), 5, self.storage, self.collection + "_prompts")
        prompt0 = prompt0.replace("<AGENTS>", "\n".join([f" - {agent['name']}: {agent['desc']}" for agent in agents if agent['name'] not in ["coder-proxy", "module-coder", "researcher"]]))

        prompt = f"""
{prompt0}

End of general instructions.

Code Execution Environment: {self.platformInfo}

Active Agents: {[k+": agentType "+p.GetPromptName() for k,p in self.processor.subProcessors.items()]}

Variables:
{self.processor.EnvSummary()}

Relevant Information: {self.Recall(context).strip()}
The "Relevant Information" part contains data that may be related to the current task, originating from your own history or the histories of other agents. Please refrain from attempting to invoke functions mentioned in the relevant information, as you may not necessarily have the permissions to do so.

"""
        #prompt += "\nConversations:"
        return self.formatter(prompt0 = prompt, conversations = self.conversations.GetConversations(frm = -n))
    
    def BuildPrompt(self):
        prompt, n = ConstructOptPrompt(self.ParameterizedBuildPrompt, low=1, high=len(self.conversations), maxLen=int(self.processor.llm.contextWindow * config.contextWindowRatio))
        if prompt is None:
            prompt, _ = self.ParameterizedBuildPrompt(1)
        return prompt
    
APrompt = APromptCoderProxy