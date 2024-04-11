from importlib.resources import read_text
from ailice.common.AConfig import config
from ailice.prompts.ARegex import GenerateRE4FunctionCalling
from ailice.prompts.ATools import ConstructOptPrompt, FindRelatedRecords

class APromptCoderProxy():
    PROMPT_NAME = "coder-proxy"
    PROMPT_DESCRIPTION = "They are adept at using programming to solve problems and has execution permissions for both Bash and Python."

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
                         "SAVE2FILE": [{"re": GenerateRE4FunctionCalling("SAVE2FILE<!|filePath: str, code: str|!> -> str"), "isEntry": True}],
                         "SCREENSHOT": [{"re": GenerateRE4FunctionCalling("SCREENSHOT<!||!> -> AImage"), "isEntry": True}],
                         "READIMAGE": [{"re": GenerateRE4FunctionCalling("READIMAGE<!|path: str|!> -> AImage", faultTolerance=True), "isEntry": True}],
                         "WRITEIMAGE": [{"re": GenerateRE4FunctionCalling("WRITEIMAGE<!|image: AImage, path: str|!>"), "isEntry": True}],
                         "BASH": [{"re": GenerateRE4FunctionCalling("BASH<!|code: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "PYTHON": [{"re": GenerateRE4FunctionCalling("PYTHON<!|code: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "CHECKOUTPUT": [{"re": GenerateRE4FunctionCalling("CHECKOUTPUT<!|session: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SCROLLUPTERM": [{"re": GenerateRE4FunctionCalling("SCROLLUPTERM<!|session: str|!> -> str"), "isEntry": True}],
                         "WAIT": [{"re": GenerateRE4FunctionCalling("WAIT<!|duration: int|!> -> str"), "isEntry": True}]}
        self.ACTIONS= {}
        return
    
    def Reset(self):
        return
    
    def GetPatterns(self):
        functions = FindRelatedRecords("programming, debugging, file operation, system operation.", len(self.PATTERNS) + 10, self.storage, self.collection + "_functions")
        self.functions = [f for f in functions if f['action'] not in self.PATTERNS]
        patterns = {f['action']: [{"re": GenerateRE4FunctionCalling(f['signature'], faultTolerance = True), "isEntry": True}] for f in self.functions}
        patterns.update(self.PATTERNS)
        return patterns
    
    def GetActions(self):
        return self.ACTIONS
    
    def Recall(self, key: str):
        ret = self.storage.Query(self.collection, key, num_results=4)
        for r in ret:
            if (key not in r[0]) and (r[0] not in key):
                return r[0]
        return "None."
    
    def ParameterizedBuildPrompt(self, n: int):
        context = self.conversations.GetConversations(frm = -1)[0]['msg']
        prompt0 = self.prompt0.replace("<FUNCTIONS>", "\n\n".join([f"#{f['prompt']}\n{f['signature']}" for f in self.functions]))
        
        prompt = f"""
{prompt0}

End of general instructions.

Active Agents: {[k+": agentType "+p.GetPromptName() for k,p in self.processor.subProcessors.items()]}

Variables:
{self.processor.EnvSummary()}

Relevant Information: {self.Recall(context).strip()}
The "RELEVANT INFORMATION" part contains data that may be related to the current task, originating from your own history or the histories of other agents. Please refrain from attempting to invoke functions mentioned in the relevant information, as you may not necessarily have the permissions to do so.

"""
        #prompt += "\nConversations:"
        ret = self.formatter(prompt0 = prompt, conversations = self.conversations.GetConversations(frm = -n))
        return ret, self.formatter.Len(ret)
    
    def BuildPrompt(self):
        prompt, n = ConstructOptPrompt(self.ParameterizedBuildPrompt, low=1, high=len(self.conversations), maxLen=int(self.processor.llm.contextWindow * config.contextWindowRatio))
        if prompt is None:
            prompt, _ = self.ParameterizedBuildPrompt(1)
        return prompt
    
APrompt = APromptCoderProxy