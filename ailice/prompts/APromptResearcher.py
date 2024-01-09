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
                         "QUERY": [{"re": GenerateRE4FunctionCalling("QUERY<!|keywords: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "VAR": [{"re": GenerateRE4FunctionCalling("VAR<!|name: str, content: str|!> -> None", faultTolerance = True), "isEntry": True}]}
        self.ACTIONS = {"VAR": {"func": self.Var}}
        self.variables = dict()
        return
    
    def Var(self, name: str, content: str):
        self.variables[name] = content
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

    def ParameterizedBuildPrompt(self, n: int):
        context = str(self.formatter(prompt0 = "", conversations = self.conversations.GetConversations(frm = -1), encode = False))
        prompt = f"""
{self.prompt0}

End of general instructions.

Active Agents: {[k+": agentType "+p.GetPromptName() for k,p in self.processor.subProcessors.items()]}

Variables:
{[f"{varName}: {content}" for varName, content in self.variables.items()]}

Relevant Information: {self.Recall(context).strip()}

"""
        #print(prompt)
        ret = self.formatter(prompt0 = prompt, conversations = self.conversations.GetConversations(frm = -n))
        return ret, self.formatter.Len(ret)
    
    def BuildPrompt(self):
        prompt, n = ConstructOptPrompt(self.ParameterizedBuildPrompt, low=1, high=len(self.conversations), maxLen=int(self.processor.llm.contextWindow * config.contextWindowRatio))
        if prompt is None:
            prompt = self.ParameterizedBuildPrompt(1)
        return prompt