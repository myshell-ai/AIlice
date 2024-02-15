import re
import random
from typing import Any
from ailice.common.ADataType import typeMap

class AConversations():
    def __init__(self):
        self.conversations: list[dict] = []
        return
    
    def Add(self, role: str, msg: str, env: dict[str,Any]):
        record = {"role": role, "msg": msg, "attachments": {}}
        
        if role in ["USER", "SYSTEM"]:
            matches = re.findall(r"```(\w*)\n([\s\S]*?)```", msg)
            vars = []
            for language, code in matches:
                varName = f"code_{language}_{str(random.randint(0,10000))}"
                env[varName] = code
                vars.append(varName)
            if 0 < len(vars):
                record['msg'] += f"\nSystem notification: The code snippets in triple backticks have been stored in variables in order: {vars}\n"
            
            matches = [m for m in re.findall(r'<([a-z]+)\|([a-zA-Z0-9_]+)\|([a-z]+)>', msg) if (m[0]==m[2]) and (m[0] in typeMap.values())]
            for label, varName, _ in matches:
                if varName in env:
                    record["attachments"][varName] = {"type": typeMap[type(env[varName])], "content": env[varName]}
                else:
                    msgNew = msg.replace(f"<{label}|{varName}|{label}>", f"<{label}|{varName}|{label}> (Error: {varName} not found in env.)")
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