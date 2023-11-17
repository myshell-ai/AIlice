from collections import deque
from utils.AFileUtils import LoadTXTFile
from prompts.ARegex import GenerateRE4FunctionCalling

class APromptRecurrent():
    PROMPT_NAME = "researcher"
    
    def __init__(self, processor, storage, collection, conversations, formatter, outputCB = None):
        self.processor = processor
        self.storage = storage
        self.collection = collection
        self.conversations = conversations
        self.formatter = formatter
        self.outputCB = outputCB
        self.prompt0 = LoadTXTFile("prompts/prompt_recurrent.txt")
        self.taskSummary = "None."
        self.previousParagraph = "None."
        self.previousActions = deque(maxlen=5)
        self.PATTERNS = {"CALL": [{"re": GenerateRE4FunctionCalling("CALL<!|agentType: str, agentName: str, msg: str|!> -> str"), "isEntry": True}],
                         "RESPOND": [{"re": GenerateRE4FunctionCalling("RESPOND<!|message: str|!> -> None", faultTolerance = True), "isEntry": True}],
                         "BROWSE": [{"re": GenerateRE4FunctionCalling("BROWSE<!|url: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SCROLLDOWN": [{"re": GenerateRE4FunctionCalling("SCROLLDOWN<!||!> -> str", faultTolerance = True), "isEntry": True}],
                         "BASH": [{"re": GenerateRE4FunctionCalling("BASH<!|cmd: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SCROLLUPBASH": [{"re": GenerateRE4FunctionCalling("SCROLLUPBASH<!||!> -> str", faultTolerance = True), "isEntry": True}],
                         "PYTHON": [{"re": GenerateRE4FunctionCalling("PYTHON<!|code: str|!> -> str", faultTolerance = True), "isEntry": True}],
                         "SCROLLUPPY": [{"re": GenerateRE4FunctionCalling("SCROLLUPPY<!||!> -> str", faultTolerance = True), "isEntry": True}],
                         "Memory": [{"re": r"Updated Working Memory:(?P<newState>.*?)Execute:", "isEntry": True}],
                         "Output": [{"re": r"New Paragraph:(?P<txt>.*?)Update:", "isEntry": True}],
                         "Action": [{"re": r"Function Call:(?P<newAction>.*)", "isEntry": True}],
                         "COMPLETE": [{"re": GenerateRE4FunctionCalling("COMPLETE<!|result: str|!> -> None", faultTolerance = True), "isEntry": True}]}
        self.ACTIONS = {"Memory": {"func": self.UpdateState},
                        "Output": {"func": self.Output},
                        "Action": {"func": self.UpdateAction}}
        return
    
    def Reset(self):
        self.taskSummary = "None."
        self.previousParagraph = "None."
        self.previousActions.clear()
        return
    
    def UpdateState(self, newState: str):
        self.taskSummary = newState
        return
    
    def UpdateAction(self, newAction: str):
        self.previousActions.append(newAction)
        return

    def Output(self, txt: str):
        txt = txt.strip()
        self.storage.Store(self.collection, txt)
        self.previousParagraph = txt
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
        context = self.taskSummary.strip() + "\n" + str(self.formatter(prompt0 = "", conversations = self.conversations.GetConversations(frm = -1), encode = False))
        prompt = f"""
{self.prompt0}

End of general instructions.

Active Agents: {[k+": agentType "+p.GetPromptName() for k,p in self.processor.subProcessors.items()]}
Previous Working Memory: {self.taskSummary.strip()}
Previous Paragraph: {self.previousParagraph.strip()}
Previous Function Call Sequence: {[a.strip() for a in self.previousActions]}
Relevant Information: {self.Recall(context).strip()}

"""
        #print(prompt)
        return self.formatter(prompt0 = prompt, conversations = self.conversations.GetConversations(frm = -1))
    