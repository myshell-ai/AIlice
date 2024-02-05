import re
import inspect
import random
import traceback
from typing import Any
from ailice.common.ADataType import typeMap
from ailice.prompts.ARegex import GenerateRE4FunctionCalling, VAR_DEF

def HasReturnValue(action):
    return action['signature'].return_annotation != inspect.Parameter.empty

class AInterpreter():
    def __init__(self):
        self.actions = {}#nodeType: {"func": func}
        self.patterns = {}#nodeType: [(pattern,isEntry)]
        self.env = {}

        self.RegisterPattern("_VAR", VAR_DEF, True)
        self.RegisterAction("_VAR", {"func": self.EvalVar})
        self.RegisterPattern("_PRINT", GenerateRE4FunctionCalling("PRINT<!|varName: str|!> -> str", faultTolerance = True), True)
        self.RegisterAction("_PRINT", {"func": self.EvalPrint})
        self.RegisterPattern("_VAR_REF", r"\$(?P<varName>[a-zA-Z0-9_]+)", False)
        self.RegisterAction("_VAR_REF", {"func": self.EvalVarRef})
        return
    
    def RegisterAction(self, nodeType: str, action: dict):
        signature = inspect.signature(action["func"])
        if not all([param.annotation != inspect.Parameter.empty for param in signature.parameters.values()]):
            print("Need annotations in registered function. node type: ", nodeType)
            exit()
        self.actions[nodeType] = {k:v for k,v in action.items()}
        self.actions[nodeType]["signature"] = signature
        return
    
    def RegisterPattern(self, nodeType: str, pattern: str, isEntry: bool):
        if nodeType not in self.patterns:
            self.patterns[nodeType] = []
        self.patterns[nodeType].append({"re": pattern, "isEntry": isEntry})
        return
    
    def EndChecker(self, txt: str) -> bool:
        endPatterns = [p['re'] for nodeType,patterns in self.patterns.items() for p in patterns if (HasReturnValue(self.actions[nodeType]) and p['isEntry'])]
        return any([bool(re.findall(pattern, txt, re.DOTALL)) for pattern in endPatterns])
    
    def GetEntryPatterns(self) -> dict[str,str]:
        return [(nodeType, p['re']) for nodeType,patterns in self.patterns.items() for p in patterns if p["isEntry"]]
    
    def Parse(self, txt: str) -> tuple[str,dict[str,str]]:
        for nodeType, patterns in self.patterns.items():
            for p in patterns:
                m = re.fullmatch(p['re'], txt, re.DOTALL)
                if m:
                    return (nodeType, m.groupdict())
        return (None, None)

    def CallWithTextArgs(self, nodeType, txtArgs):
        action = self.actions[nodeType]
        #print(f"action: {action}, {txtArgs}")
        signature = action["signature"]
        if set(txtArgs.keys()) != set(signature.parameters.keys()):
            return "The function call failed because the arguments did not match. txtArgs.keys(): " + str(txtArgs.keys()) + ". func params: " + str(signature.parameters.keys())
        paras = dict()
        for k,v in txtArgs.items():
            v = self.Eval(v)
            if str == signature.parameters[k].annotation:
                paras[k] = str(v.strip('"\'')) if (len(v) > 0) and (v[0] == v[-1]) and (v[0] in ["'",'"']) else str(v)
            else:
                paras[k] = signature.parameters[k].annotation(v)
        try:
            ret = action['func'](**paras)
        except Exception as e:
            ret = str(e) + f"EXCEPTION: {str(e)}\n{traceback.format_exc()}"
        
        if type(ret) in typeMap:
            varName = f"{nodeType}_ret_{typeMap[type(ret)]}_{str(random.randint(0,10000))}"
            self.env[varName] = ret
            ret = f"The data of {typeMap[type(ret)]} type is returned and has been stored in a variable named '{varName}'."
        else:
            ret = f"{nodeType}_RESULT: [{ret}]"
        return ret
    
    def Eval(self, txt: str) -> str:
        nodeType, paras = self.Parse(txt)
        if None == nodeType:
            return txt
        else:
            r = self.CallWithTextArgs(nodeType, paras)
            return r if r is not None else ""

    def ParseEntries(self, txt_input: str) -> list[str]:
        matches = []
        for nodeType, pattern in self.GetEntryPatterns():
            for match in re.finditer(pattern, txt_input, re.DOTALL):
                matches.append(match)
            
        ret = []
        #Here we assume that a match will not appear multiple times in matches. This is reasonable.
        for match in matches:
            isSubstring = any(
                (m.start() <= match.start()) and (m.end() >= match.end()) and (m is not match)
                for m in matches
            )
            if not isSubstring:
                ret.append(match.group(0))
        return ret

    def EvalEntries(self, txt: str) -> str:
        scripts = self.ParseEntries(txt)
        resp = ""
        for script in scripts:
            r = self.Eval(script)
            if "" != r:
                resp += (r + "\n")
        return resp
    
    def EvalVarRef(self, varName: str) -> Any:
        if varName in self.env:
            return self.env[varName]
        else:
            return f"{varName} NOT DEFINED."

    def EvalVar(self, varName: str, content: str):
        self.env[varName] = content
        return
    
    def EvalPrint(self, varName: str) -> str:
        if varName in self.env:
            return self.env[varName]
        else:
            return f"ERROR: {varName} not defined."