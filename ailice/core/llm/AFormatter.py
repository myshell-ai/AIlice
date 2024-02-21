import copy
import io

class AFormatterVicuna():
    def __init__(self, tokenizer=None, systemAsUser = False):
        self.tokenizer = tokenizer
        self.systemAsUser = systemAsUser
    
    def __call__(self, prompt0, conversations, encode = True, assistTag = True):
        sep = {"USER": " ", "ASSISTANT": "</s>", "SYSTEM": " "}
        roleMap = {"USER": "USER", "ASSISTANT": "ASSISTANT", "SYSTEM": "SYSTEM" if not self.systemAsUser else "USER"}
        ret = prompt0 + "\n" + "".join([roleMap[c['role']] + ": " + c['msg'] + sep[roleMap[c['role']]] for c in conversations]) + (" ASSISTANT:" if assistTag else "")
        #print("prompt: ", ret)
        return self.tokenizer.encode(ret) if encode else ret
    
    def Len(self, prompt) -> int:
        return len(prompt)
    
class AFormatterLLAMA2():
    def __init__(self, tokenizer=None, systemAsUser = False):
        self.tokenizer = tokenizer
        self.systemAsUser = systemAsUser
    
    def __call__(self, prompt0, conversations, encode = True, assistTag = True):
        B_INST="[INST]"
        E_INST="[/INST]"
        B_SYS="<<SYS>>\n"
        E_SYS="\n<</SYS>>\n\n"
        
        roleMap = {"USER": "USER", "ASSISTANT": "ASSISTANT", "SYSTEM": "SYSTEM" if not self.systemAsUser else "USER"}
        conv = [{'role': roleMap[c['role']], 'msg': c['msg']} for c in copy.deepcopy(conversations)]
        
        conv[0]['msg'] = (B_SYS + prompt0 + E_SYS + conv[0]["msg"]) if self.systemAsUser or ("SYSTEM" != conv[0]['role']) else (prompt0 + conv[0]["msg"])
        conv = [{"role": c["role"], "msg": B_SYS + c["msg"] + E_SYS} if "SYSTEM" == c["role"] else c for c in conv]

        if encode:
            assert len(conversations) % 2 == 1, "conversations has an even length. "
            
            self.tokenizer.add_bos_token=True
            self.tokenizer.add_eos_token=True
            
            ret = sum([self.tokenizer.encode(f"{B_INST} {prompt['msg'].strip()} {E_INST} {answer['msg'].strip()} ") for prompt,answer in zip(conv[0::2], conv[1::2])],
                        [])
            if assistTag and (1 == (len(conv) % 2)):
                self.tokenizer.add_bos_token=True
                self.tokenizer.add_eos_token=False
                ret += self.tokenizer.encode(f"{B_INST} {conv[-1]['msg'].strip()} {E_INST}")
            #print("\n prompt: ", self.tokenizer.decode(ret))
        else:
            ret = sum([f"{B_INST} {prompt['msg'].strip()} {E_INST} {answer['msg'].strip()} " for prompt,answer in zip(conv[0::2], conv[1::2])],
                        [])
            if assistTag and (1 == (len(conv) % 2)):
                ret += f"{B_INST} {conv[-1]['msg'].strip()} {E_INST}"
            #print("\n prompt: ", ret)
        return ret

    def Len(self, prompt) -> int:
        return len(prompt)
    
class AFormatterSimple():
    def __init__(self, tokenizer=None, systemAsUser = False):
        self.tokenizer = tokenizer
        self.systemAsUser = systemAsUser

    def __call__(self, prompt0, conversations, encode = True, assistTag = True):
        roleMap={'USER': 'User', 'ASSISTANT': 'Assistant', 'SYSTEM': 'System' if not self.systemAsUser else "User"}
        seps={'USER': "\n", 'ASSISTANT': "\n", 'SYSTEM': "\n"}

        ret = prompt0 + "\n" + "".join([f"### {roleMap[c['role']]}:\n{c['msg']}{seps[c['role']]}" for c in conversations]) + (f"### {roleMap['ASSISTANT']}:\n" if assistTag else "")
        #print("prompt: ", ret)
        return self.tokenizer.encode(ret) if encode else ret

    def Len(self, prompt) -> int:
        return len(prompt)

class AFormatterChatML():
    def __init__(self, tokenizer=None, systemAsUser = False):
        self.START = "<|im_start|>"
        self.END = "<|im_end|>"
        self.roles={'USER': 'user', 'ASSISTANT': 'assistant', 'SYSTEM': 'system'}
        self.left={'USER': self.START, 'ASSISTANT': self.START, 'SYSTEM': self.START}
        self.right={'USER': self.END + "\n", 'ASSISTANT': self.END  + "\n", 'SYSTEM': self.END  + "\n"}
        self.tokenizer = tokenizer
        self.systemAsUser = systemAsUser
    
    def BuildMsg(self, role: str, msg: str):
        if self.systemAsUser and "SYSTEM" == role:
            role = "USER"
        return f"{self.left[role]}{self.roles[role]}\n{msg}{self.right[role]}"
    
    def __call__(self, prompt0, conversations, encode = True, assistTag = True):
        ret = f"{self.START}system\n{prompt0}\n{self.END}\n" + "".join([self.BuildMsg(c["role"], c["msg"]) for c in conversations]) + (f"{self.START}assistant\n" if assistTag else "")
        #print("prompt: ", ret)
        return self.tokenizer.encode(ret) if encode else ret

    def Len(self, prompt) -> int:
        return len(prompt)

class AFormatterAMAZON():
    def __init__(self, tokenizer=None, systemAsUser = False):
        #self.roles={'USER': 'user', 'ASSISTANT': 'assistant', 'SYSTEM': 'system'}
        self.left={'USER': "<|prompter|>", 'ASSISTANT': "<|assistant|>", 'SYSTEM': ""}
        self.right={'USER': "</s>", 'ASSISTANT': "</s>", 'SYSTEM': ""}
        self.tokenizer = tokenizer
        self.systemAsUser = systemAsUser
    
    def BuildMsg(self, role: str, msg: str):
        if self.systemAsUser and "SYSTEM" == role:
            role = "USER"
        return f"{self.left[role]}{msg}{self.right[role]}"
    
    def __call__(self, prompt0, conversations, encode = True, assistTag = True):
        ret = f"{self.left['SYSTEM']}{prompt0}{self.right['SYSTEM']}" + "".join([self.BuildMsg(c["role"], c["msg"]) for c in conversations]) + (f"<|assistant|>" if assistTag else "")
        #print("prompt: ", ret)
        return self.tokenizer.encode(ret) if encode else ret

    def Len(self, prompt) -> int:
        return len(prompt)

class AFormatterZephyr():
    def __init__(self, tokenizer=None, systemAsUser = False):
        #self.roles={'USER': 'user', 'ASSISTANT': 'assistant', 'SYSTEM': 'system'}
        self.left={'USER': "<|user|>\n", 'ASSISTANT': "<|assistant|>\n", 'SYSTEM': "<|system|>\n"}
        self.right={'USER': "</s>\n", 'ASSISTANT': "</s>\n", 'SYSTEM': "</s>\n"}
        self.tokenizer = tokenizer
        self.systemAsUser = systemAsUser
    
    def BuildMsg(self, role: str, msg: str):
        if self.systemAsUser and "SYSTEM" == role:
            role = "USER"
        return f"{self.left[role]}{msg}{self.right[role]}"
    
    def __call__(self, prompt0, conversations, encode = True, assistTag = True):
        ret = f"{self.left['SYSTEM']}{prompt0}{self.right['SYSTEM']}" + "".join([self.BuildMsg(c["role"], c["msg"]) for c in conversations]) + (f"<|assistant|>" if assistTag else "")
        #print("prompt: ", ret)
        return self.tokenizer.encode(ret) if encode else ret

    def Len(self, prompt) -> int:
        return len(prompt)

class AFormatterOpenChat():
    def __init__(self, tokenizer=None, systemAsUser = False):
        self.left={'USER': "GPT4 User:", 'ASSISTANT': "GPT4 Assistant:", 'SYSTEM': "GPT4 System:"}
        self.right={'USER': "<|end_of_turn|>", 'ASSISTANT': "<|end_of_turn|>", 'SYSTEM': "<|end_of_turn|>"}
        self.tokenizer = tokenizer
        self.systemAsUser = systemAsUser
    
    def BuildMsg(self, role: str, msg: str):
        if self.systemAsUser and "SYSTEM" == role:
            role = "USER"
        return f"{self.left[role]}{msg}{self.right[role]}"
    
    def __call__(self, prompt0, conversations, encode = True, assistTag = True):
        ret = f"{prompt0}{self.right['SYSTEM']}" + "".join([self.BuildMsg(c["role"], c["msg"]) for c in conversations]) + (f"{self.left['ASSISTANT']}" if assistTag else "")
        #print("prompt: ", ret)
        return self.tokenizer.encode(ret) if encode else ret

    def Len(self, prompt) -> int:
        return len(prompt)

class AFormatterGPT():
    def __init__(self, tokenizer=None, systemAsUser = False):
        self.systemAsUser = systemAsUser
        return
    
    def __call__(self, prompt0, conversations, encode = True, assistTag = True):
        roleMap = {"SYSTEM": "system" if not self.systemAsUser else "user", "USER": "user", "ASSISTANT": "assistant"}
        ret = [{"role": "system", "content": prompt0}] + [{"role": roleMap[c['role']], "content": c['msg']} for c in conversations]
        #print("prompt: ", ret)
        return ret

    def Len(self, prompt) -> int:
        return len(str(prompt)) // 4

class AFormatterGPTVision():
    def __init__(self, tokenizer=None, systemAsUser = False):
        self.systemAsUser = systemAsUser
        self.typeConvert = {"image": "image_url"}
        return
    
    def BuildMsg(self, role: str, msg: str, attachments: list):
        roleMap = {"SYSTEM": "system" if not self.systemAsUser else "user", "USER": "user", "ASSISTANT": "assistant"}
        return {"role": roleMap[role],
                "content": [{"type": "text", "text": msg}] +
                           [{"type": self.typeConvert[a['type']], self.typeConvert[a['type']]: {"url": f"data:image/jpeg;base64,{a['content'].ToJson()['data']}"}} for a in attachments if (a['type'] in ["image"])]}
        
    def __call__(self, prompt0, conversations, encode = True, assistTag = True):
        ret = [{"role": "system", "content": [{"type": "text", "text": prompt0}]}] + [self.BuildMsg(c['role'], c['msg'], c['attachments']) for c in conversations]
        #print("prompt: ", ret)
        return ret

    def Len(self, prompt) -> int:
        return len(str(prompt)) // 4

def CreateFormatter(formatterClsName: str, tokenizer, systemAsUser):
    formatterList = [AFormatterSimple, AFormatterLLAMA2, AFormatterVicuna, AFormatterChatML, AFormatterAMAZON, AFormatterZephyr, AFormatterOpenChat, AFormatterGPT, AFormatterGPTVision]
    for formatterCls in formatterList:
        if formatterClsName == formatterCls.__name__:
            return formatterCls(tokenizer = tokenizer, systemAsUser = systemAsUser)
    raise ValueError(f"{formatterClsName} is not a valid formatter class name.")