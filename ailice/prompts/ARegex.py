import re

ARegexMap = {"str": r"(?<!\\)'''(?:\\.|'(?!'')|[^'\\])*?'''|(?<!\\)\"\"\"(?:\\.|\"(?!\"\")|[^\"\\])*?\"\"\"|(?<!\\)'(?:\\.|[^'\\])*?'|(?<!\\)\"(?:\\.|[^\"\\])*?\"",
             "url": r"(?:\w+):\/\/(?:[^/:]+)(?::\d*)?(?:[^# ]*)",
             "int": r"[+-]?[0-9]+",
             "bool": r"True|False",
             "uint": r"[0-9]+",
             "float": r"[+-]?(?:[0-9]*[.])?[0-9]+",
             "path": r"(?:\/|(?:[A-Za-z]:)?[\\|\/])?(?:[\w\-\s\.]+[\|\/]?)*",
             "ref": r"[a-zA-Z0-9_]+"}

ARegexMap["expr_cat"] = f"(?:{ARegexMap['ref']}|{ARegexMap['str']})(?:\s*\+\s*(?:{ARegexMap['ref']}|{ARegexMap['str']}))+"

VAR_DEF = r"(?P<varName>([a-zA-Z0-9_]+))[ ]*:=[ ]*<!\|(?P<content>(.*?))\|!>"

def GenerateRE4FunctionCalling(signature: str, faultTolerance: bool = False) -> str:
    #signature: "FUNC<!|ARG1: ARG1_TYPE, ARG2: ARG2_TYPE...|!> -> RETURN_TYPE"
    pattern = r"(\w+)<!\|((?:\w+[ ]*:[ ]*[\w,\. ]+)*)\|!>((?:[ ]*->[ ]*)([\w\.]+))?"
    matches = re.search(pattern, signature)
    if matches is None:
        print("signature invalid. exit. ", signature)
        exit()
    funcName, args, retType = matches[1], matches[2], matches[4]
    
    pattern = r"(\w+)[ ]*:[ ]*(\w+)"
    typePairs = re.findall(pattern, args)
    
    reMap = {k: v for k,v in ARegexMap.items()}
    reMap["str"] = r"(?:.*?(?=\|!>))" if faultTolerance else ARegexMap['str']
    patternArgs = '[ ]*,[ ]*'.join([f"(?:({arg}|\"{arg}\"|\'{arg}\')[ ]*[:=][ ]*)?(?P<{arg}>({reMap.get(tp,reMap['ref'])}|{reMap['ref']}))" for arg,tp in typePairs])
    return rf"!{funcName}<!\|[ ]*{patternArgs}[ ]*\|!>"
