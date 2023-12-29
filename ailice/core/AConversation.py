class AConversations():
    def __init__(self):
        self.conversations: list[dict[str,str]] = []
        return
    
    def Add(self, role: str, msg: str):
        self.conversations.append({"role": role, "msg": msg})
        return
    
    def GetConversations(self, frm=0):
        s = (2*frm) if (frm >= 0) or ('ASSISTANT' == self.conversations[-1]['role']) else (2*frm+1)
        return self.conversations[s:]
    
    def __len__(self):
        return (len(self.conversations)+1) // 2
    
    def ToJson(self) -> str:
        return self.conversations