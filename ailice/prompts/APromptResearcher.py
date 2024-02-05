from importlib.resources import read_text
from ailice.common.AConfig import config
from ailice.prompts.ARegex import GenerateRE4FunctionCalling
from ailice.prompts.ATools import ConstructOptPrompt


class APromptResearcher():
    PROMPT_NAME = "researcher"
    
    def __init__(self, processor, storage, collection, conversations, formatter, outputCB = None):
        self.processor = processor
        self.storage = storage
        self.collection = collection
        self.conversations = conversations
        self.formatter = formatter
        self.outputCB = outputCB
        self.prompt0 = read_text("ailice.prompts", "prompt_researcher.txt")
        self.PATTERNS = {"CALL": [{"re": GenerateRE4FunctionCalling("CALL<!|agentType: str, agentName: str, msg: str|!> -> str"), "isEntry": True}],
                         "RESPOND": [{"re": GenerateRE4FunctionCalling("RESPOND<!|message: str|!> -> None", faultTolerance = True), "isEntry": True}],
                         "BROWSE": [{"re": GenerateRE4FunctionCalling("BROWSE<!|url: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SCROLLDOWN": [{"re": GenerateRE4FunctionCalling("SCROLLDOWN<!||!> -> str", faultTolerance = True), "isEntry": True}],
                         "SEARCHDOWN": [{"re": GenerateRE4FunctionCalling("SEARCHDOWN<!|keyword: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SEARCHUP": [{"re": GenerateRE4FunctionCalling("SEARCHUP<!|keyword: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "BASH": [{"re": GenerateRE4FunctionCalling("BASH<!|code: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SCROLLUPBASH": [{"re": GenerateRE4FunctionCalling("SCROLLUPBASH<!||!> -> str", faultTolerance = True), "isEntry": True}],
                         "PYTHON": [{"re": GenerateRE4FunctionCalling("PYTHON<!|code: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SCROLLUPPY": [{"re": GenerateRE4FunctionCalling("SCROLLUPPY<!||!> -> str", faultTolerance = True), "isEntry": True}],
                         "STORE": [{"re": GenerateRE4FunctionCalling("STORE<!|txt: str|!> -> None", faultTolerance = True), "isEntry": True}],
                         "QUERY": [{"re": GenerateRE4FunctionCalling("QUERY<!|keywords: str|!> -> str", faultTolerance = True), "isEntry": True}]}
        self.ACTIONS = {}
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

    def ParameterizedBuildPrompt(self, n: int):
        context = self.conversations.GetConversations(frm = -1)[0]['msg']
        prompt = f"""
{self.prompt0}

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