import re
import random
import ast
from typing import Any
from ailice.prompts.ARegex import ARegexMap
from ailice.common.ADataType import typeInfo


class AConversations():
    def __init__(self):
        self.conversations: list[dict] = []
        return
    
    def Add(self, role: str, msg: str, env: dict[str,Any]):
        record = {"role": role, "msg": msg, "attachments": []}
        
        if role in ["USER", "SYSTEM"]:
            matches = re.findall(r"```(\w*)\n([\s\S]*?)```", msg)
            vars = []
            for language, code in matches:
                varName = f"code_{language}_{str(random.randint(0,10000))}"
                env[varName] = code
                vars.append(varName)
            if 0 < len(vars):
                record['msg'] += f"\nSystem notification: The code snippets within the triple backticks in this message have been saved as variables, in accordance with their order in the text, the variable names are as follows: {vars}\n"
            
            matches = [m for m in re.findall(f'<([a-zA-Z0-9_]+)\\|(?:({ARegexMap["ref"]})|({ARegexMap["str"]}))\\|([a-zA-Z0-9_]+)>', msg) if (m[0]==m[3]) and (m[0] in [t.__name__ for t in typeInfo.keys()])]
            for label, varName, txt, _ in matches:
                txt = ast.literal_eval(txt) if txt not in ["", None] else ""
                try:
                    if ("" != varName) and (varName in env):
                        record["attachments"].append({"type": typeInfo[type(env[varName])]['modal'], "content": env[varName].Standardize()})
                    elif ("" != txt):
                        targetType = [t for t in typeInfo if t.__name__ == label][0]
                        record["attachments"].append({"type": typeInfo[targetType]['modal'], "content": targetType(txt).Standardize()})
                except Exception as e:
                    msgNew = msg.replace(f"<{label}|{varName}{txt}|{label}>", f"<{label}|{varName}{txt}|{label}> (Can not obtain labeled content: {e})")
                    record["msg"] = msgNew
        self.conversations.append(record)
        return
    
    def GetConversations(self, frm=0):
        s = (2*frm) if (frm >= 0) or ('ASSISTANT' == self.conversations[-1]['role']) else (2*frm+1)
        return self.conversations[s:]
    
    def __len__(self):
        return (len(self.conversations)+1) // 2
    
    def ToJson(self) -> str:
        return self.conversations