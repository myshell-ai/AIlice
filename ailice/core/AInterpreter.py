import re
import inspect
import random
import ast
import traceback
from typing import Any
from ailice.common.ADataType import typeInfo, ToJson, FromJson
from ailice.prompts.ARegex import GenerateRE4FunctionCalling, GenerateRE4ObjectExpr, ARegexMap, VAR_DEF, EXPR_OBJ
from ailice.common.AMessenger import messenger

def HasReturnValue(action):
    return action['signature'].return_annotation != inspect.Parameter.empty

class AInterpreter():
    def __init__(self):
        self.actions = {}#nodeType: {"func": func}
        self.patterns = {}#nodeType: [{re,isEntry,noTrunc}]
        self.env = {}

        self.RegisterPattern("_STR", f"(?P<txt>({ARegexMap['str']}))", False)
        self.RegisterPattern("_INT", f"(?P<txt>({ARegexMap['int']}))", False)
        self.RegisterPattern("_FLOAT", f"(?P<txt>({ARegexMap['float']}))", False)
        self.RegisterPattern("_BOOL", f"(?P<txt>({ARegexMap['bool']}))", False)
        self.RegisterPattern("_VAR", VAR_DEF, True)
        self.RegisterPattern("_PRINT", GenerateRE4FunctionCalling("PRINT<!|txt: str|!> -> str", faultTolerance = True), True)
        self.RegisterAction("_PRINT", {"func": self.EvalPrint})
        self.RegisterPattern("_VAR_REF", f"(?P<varName>({ARegexMap['ref']}))", False)
        self.RegisterPattern("_EXPR_CAT", f"(?P<expr>({ARegexMap['expr_cat']}))", False)
        for dataType in typeInfo:
            if not typeInfo[dataType]["tag"]:
                continue
            self.RegisterPattern(f"_EXPR_OBJ_{dataType.__name__}", GenerateRE4ObjectExpr(inspect.Signature([param for name,param in inspect.signature(dataType.__init__).parameters.items() if name != 'self']), dataType.__name__, faultTolerance=True), False)
            self.RegisterAction(f"_EXPR_OBJ_{dataType.__name__}", {"func": self.CreateObjCB(dataType)})
        self.RegisterPattern("_EXPR_OBJ_DEFAULT", EXPR_OBJ, False)
        self.RegisterAction("_EXPR_OBJ_DEFAULT", {"func": self.EvalObjDefault, "noEval": ["typeBra", "typeKet"]})
        return
    
    def RegisterAction(self, nodeType: str, action: dict):
        signature = inspect.signature(action["func"])
        if not all([param.annotation != inspect.Parameter.empty for param in signature.parameters.values()]):
            print("Need annotations in registered function. node type: ", nodeType)
            exit()
        self.actions[nodeType] = {k:v for k,v in action.items()}
        self.actions[nodeType]["signature"] = signature
        return
    
    def RegisterPattern(self, nodeType: str, pattern: str, isEntry: bool, noTrunc: bool = False):
        if nodeType not in self.patterns:
            self.patterns[nodeType] = []
        p = {"re": pattern, "isEntry": isEntry, "noTrunc": noTrunc}
        if p not in self.patterns[nodeType]:
            self.patterns[nodeType].append(p)
        return
    
    def CreateVar(self, content: Any, prefix: str) -> str:
        varName = f"{prefix}_{type(content).__name__}_{str(random.randint(0,10000))}"
        self.env[varName] = content
        return varName
    
    def EndChecker(self, txt: str) -> bool:
        endPatterns = [p['re'] for nodeType,patterns in self.patterns.items() for p in patterns if p['isEntry'] and (not p['noTrunc']) and (HasReturnValue(self.actions[nodeType]) if nodeType in self.actions else False)]
        return any([bool(re.findall(pattern, txt, re.DOTALL)) for pattern in endPatterns]) or (None != messenger.Get())
    
    def GetEntryPatterns(self) -> dict[str,str]:
        return [(nodeType, p['re']) for nodeType,patterns in self.patterns.items() for p in patterns if p["isEntry"]]
    
    def Parse(self, txt: str) -> tuple[str,dict[str,str]]:
        for nodeType, patterns in self.patterns.items():
            for p in patterns:
                m = re.fullmatch(p['re'], txt, re.DOTALL)
                if m:
                    return (nodeType, m.groupdict())
        return (None, None)

    def CallWithTextArgs(self, nodeType, txtArgs) -> Any:
        action = self.actions[nodeType]
        #print(f"action: {action}, {txtArgs}")
        signature = action["signature"]
        if set(txtArgs.keys()) != set(signature.parameters.keys()):
            return "The function call failed because the arguments did not match. txtArgs.keys(): " + str(txtArgs.keys()) + ". func params: " + str(signature.parameters.keys())
        paras = dict()
        for k,v in txtArgs.items():
            paras[k] = v if (k in action.get("noEval", [])) else self.Eval(v)
            if type(paras[k]) != signature.parameters[k].annotation:
                raise TypeError(f"parameter {k} should be of type {signature.parameters[k].annotation.__name__}, but got {type(paras[k]).__name__}.")
        return action['func'](**paras)
    
    def Eval(self, txt: str) -> Any:
        nodeType, paras = self.Parse(txt)
        if None == nodeType:
            return txt
        elif "_STR" == nodeType:
            return self.EvalStr(txt)
        elif "_INT" == nodeType:
            return int(txt)
        elif "_FLOAT" == nodeType:
            return float(txt)
        elif "_BOOL" ==nodeType:
            return bool(txt)
        elif "_VAR" == nodeType:
            return self.EvalVar(varName=paras['varName'], content=self.Eval(paras['content']))
        elif "_VAR_REF" == nodeType:
            return self.EvalVarRef(txt)
        elif "_EXPR_CAT" == nodeType:
            return self.EvalExprCat(txt)
        else:
            return self.CallWithTextArgs(nodeType, paras)

    def ParseEntries(self, txt_input: str) -> list[str]:
        ms = {}
        for nodeType, pattern in self.GetEntryPatterns():
            for match in re.finditer(pattern, txt_input, re.DOTALL):
                ms[(match.start(), match.end())] = match
        matches = sorted(list(ms.values()), key=lambda match: match.start())
        
        ret = []
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
            try:
                r = self.Eval(script)
                if type(r) in typeInfo:
                    varName = self.CreateVar(content=r, prefix="ret")
                    r = f"![Returned data is stored to variable: {varName} := {str(r)}]({varName})<&>"
                elif r != None:
                    r = str(r)
            except Exception as e:
                r = str(e) + f"EXCEPTION: {str(e)}\n{traceback.format_exc()}"
            if r not in ["", None]:
                resp += (r + "\n")
        return resp

    def EvalStr(self, txt: str) -> str:
        return ast.literal_eval(txt)
    
    def EvalVarRef(self, varName: str) -> Any:
        if varName in self.env:
            return self.env[varName]
        else:
            raise ValueError(f'Variable name {varName} NOT FOUND, did you mean to use a string "{varName}" but forgot the quotation marks?')

    def EvalVar(self, varName: str, content: Any):
        self.env[varName] = content
        return
    
    def EvalExprCat(self, expr: str) -> str:
        pattern = f"{ARegexMap['str']}|{ARegexMap['ref']}"
        ret = ""
        for match in re.finditer(pattern, expr):
            ret += self.Eval(match.group(0))
        return ret
    
    def EvalObjDefault(self, typeBra: str, args: str, typeKet: str) -> Any:
        if typeBra != typeKet:
            raise ValueError(f"The left and right types in braket should be the same. But in fact the left side is ({typeBra}), and the right side is ({typeKet}). Please correct your syntax.")
        if typeBra not in [t.__name__ for t in typeInfo.keys()]+['&', '!']:
            raise ValueError(f"The specified object type ({typeBra}) is not supported. Please check your input.")
        if "!" == typeBra.strip():
            return args
        elif "&" == typeBra.strip():
            return self.env.get(args.strip())
        else:
            raise ValueError(f"It looks like you are trying to create an object of type ({typeBra}), but syntax parsing fails for unrecognized reasons. Please check your syntax.")
    
    def EvalPrint(self, txt: str) -> str:
        return txt
    
    def CreateObjCB(self, dataType):
        def callback(*args,**kwargs):
            return dataType(*args,**kwargs)
        newSignature = inspect.Signature(parameters=[inspect.Parameter(name=t.name, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=t.annotation) for p,t in inspect.signature(dataType.__init__).parameters.items() if t.name != 'self'],
                                         return_annotation=dataType)
        callback.__signature__ = newSignature
        return callback
    
    def ToJson(self):
        return {"env": {k: ToJson(v) for k,v in self.env.items()}}
    
    def FromJson(self, data):
        self.env = {k: FromJson(v) for k,v in data['env'].items()}
        return