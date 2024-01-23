import re
import inspect
from inspect import Parameter, Signature

def HasReturnValue(action):
    return action['signature'].return_annotation != inspect.Parameter.empty

class AInterpreter():
    def __init__(self):
        self.actions = {}#nodeType: {"func": func}
        self.patterns = {}#nodeType: [(pattern,isEntry)]
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
        endPatterns = [p['re'] for nodeType,patterns in self.patterns.items() for p in patterns if HasReturnValue(self.actions[nodeType])]
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

    def CallWithTextArgs(self, action, txtArgs):
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
            ret = str(e)
        return ret
    
    def Eval(self, txt: str) -> str:
        nodeType, paras = self.Parse(txt)
        if None == nodeType:
            return txt
        else:
            r = self.CallWithTextArgs(self.actions[nodeType], paras)
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

