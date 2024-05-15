import re

ARegexMap = {"str": r"(?<!\\)'''(?:\\.|'(?!'')|[^'\\])*?'''|(?<!\\)\"\"\"(?:\\.|\"(?!\"\")|[^\"\\])*?\"\"\"|(?<!\\)'(?:\\.|[^'\\])*?'|(?<!\\)\"(?:\\.|[^\"\\])*?\"",
             "url": r"(?:\w+):\/\/(?:[^/:]+)(?::\d*)?(?:[^# ]*)",
             "int": r"[+-]?[0-9]+",
             "bool": r"True|False",
             "uint": r"[0-9]+",
             "float": r"[+-]?(?:[0-9]*[.])?[0-9]+",
             "path": r"(?:\/|(?:[A-Za-z]:)?[\\|\/])?(?:[\w\-\s\.]+[\|\/]?)*",
             "ref": r"[a-zA-Z0-9_\-]+"}

ARegexMap["expr_cat"] = rf"(?:{ARegexMap['ref']}|{ARegexMap['str']})(?:\s*\+\s*(?:{ARegexMap['ref']}|{ARegexMap['str']}))+"

EXPR_OBJ = r"<(?P<typeBra>([a-zA-Z0-9_&!]+))\|(?P<args>(.*?))\|(?P<typeKet>([a-zA-Z0-9_&!]+))>"
VAR_DEF = r"(?P<varName>([a-zA-Z0-9_\-]+))\s*:=\s*(?P<content>(?:<([a-zA-Z0-9_&!]+)\|(?:.*?)\|([a-zA-Z0-9_&!]+)>))"

def GenerateRE4FunctionCalling(signature: str, faultTolerance: bool = False) -> str:
    #signature: "FUNC<!|ARG1: ARG1_TYPE, ARG2: ARG2_TYPE...|!> -> RETURN_TYPE"
    pattern = r"(\w+)<!\|((?:\w+\s*:\s*[\w,\. ]+)*)\|!>((?:\s*->\s*)([\w\.]+))?"
    matches = re.search(pattern, signature)
    if matches is None:
        print("signature invalid. exit. ", signature)
        exit()
    funcName, args, retType = matches[1], matches[2], matches[4]
    
    pattern = r"(\w+)\s*:\s*(\w+)"
    typePairs = re.findall(pattern, args)
    
    reMap = {k: v for k,v in ARegexMap.items()}
    reMap["str"] = r"(.*?(?=(?:\s*)\|!>))" if (faultTolerance and 1==len(typePairs) and "str"==typePairs[0][1]) else ARegexMap['str']
    refOrcatOrObj = rf"{reMap['ref']}|{reMap['expr_cat']}|(?:<([a-zA-Z0-9_&!]+)\|(?:.*?)\|([a-zA-Z0-9_&!]+)>)"
    patternArgs = r'\s*,\s*'.join([rf"(?:({arg}|\"{arg}\"|\'{arg}\')\s*[:=]\s*)?(?P<{arg}>({reMap[tp]+'|' if tp in reMap else ''}{refOrcatOrObj}))" for arg,tp in typePairs])
    return rf"!{funcName}<!\|\s*{patternArgs}\s*\|!>"

def GenerateRE4ObjectExpr(signature, typeName: str, faultTolerance:bool = False) -> str:
    typePairs = [(param.name, param.annotation.__name__) for name, param in signature.parameters.items()]
    reMap = {k: v for k,v in ARegexMap.items()}
    reMap["str"] = rf"(?:.*?(?=\|{typeName}>))" if (faultTolerance and 1==len(typePairs) and "str"==typePairs[0][1]) else ARegexMap['str']
    patternArgs =  r'\s*,\s*'.join([rf"(?:({arg}|\"{arg}\"|\'{arg}\')\s*[:=]\s*)?(?P<{arg}>({reMap[tp]}))" for arg,tp in typePairs])
    return rf"<(?:{typeName})\|\s*{patternArgs}\s*\|(?:{typeName})>"