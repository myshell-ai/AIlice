import copy
import inspect
import io
import av
from ailice.common.ADataType import AImage
from ailice.core.llm.ATokenEstimator import TokenEstimatorOAI

class AFormatterVicuna():
    def __init__(self, tokenizer=None, systemAsUser = False):
        self.tokenizer = tokenizer
        self.systemAsUser = systemAsUser
    
    def __call__(self, prompt0, conversations, encode = True, assistTag = True):
        sep = {"USER": " ", "ASSISTANT": "</s>", "SYSTEM": " "}
        roleMap = {"USER": "USER", "ASSISTANT": "ASSISTANT", "SYSTEM": "SYSTEM" if not self.systemAsUser else "USER"}
        ret = prompt0 + "\n" + "".join([roleMap[c['role']] + ": " + c['msg'] + sep[roleMap[c['role']]] for c in conversations]) + (" ASSISTANT:" if assistTag else "")
        #print("prompt: ", ret)
        tokens = self.tokenizer.encode(ret)
        return (tokens, len(tokens)) if encode else (ret, len(tokens))
    
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

        assert len(conversations) % 2 == 1, "conversations has an even length. "
        
        self.tokenizer.add_bos_token=True
        self.tokenizer.add_eos_token=True
        
        tokens = sum([self.tokenizer.encode(f"{B_INST} {prompt['msg'].strip()} {E_INST} {answer['msg'].strip()} ") for prompt,answer in zip(conv[0::2], conv[1::2])],
                    [])
        if assistTag and (1 == (len(conv) % 2)):
            self.tokenizer.add_bos_token=True
            self.tokenizer.add_eos_token=False
            tokens += self.tokenizer.encode(f"{B_INST} {conv[-1]['msg'].strip()} {E_INST}")
        #print("\n prompt: ", self.tokenizer.decode(ret))
        if not encode:
            ret = sum([f"{B_INST} {prompt['msg'].strip()} {E_INST} {answer['msg'].strip()} " for prompt,answer in zip(conv[0::2], conv[1::2])],
                        [])
            if assistTag and (1 == (len(conv) % 2)):
                ret += f"{B_INST} {conv[-1]['msg'].strip()} {E_INST}"
            #print("\n prompt: ", ret)
        return (tokens, len(tokens)) if encode else (ret, len(tokens))

class AFormatterLLAMA3():
    def __init__(self, tokenizer=None, systemAsUser = False):
        self.roles={'USER': "user", 'ASSISTANT': "assistant", 'SYSTEM': "system"}
        self.tokenizer = tokenizer
        self.systemAsUser = systemAsUser
    
    def BuildMsg(self, role: str, msg: str):
        if self.systemAsUser and "SYSTEM" == role:
            role = "USER"
        return f"<|start_header_id|>{self.roles[role]}<|end_header_id|>\n{msg}<|eot_id|>"
    
    def __call__(self, prompt0, conversations, encode = True, assistTag = True):
        ret = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{prompt0}<|eot_id|>" + "".join([self.BuildMsg(c["role"], c["msg"]) for c in conversations]) + (f"<|start_header_id|>{self.roles['ASSISTANT']}<|end_header_id|>\n" if assistTag else "")
        #print("prompt: ", ret)
        tokens = self.tokenizer.encode(ret)
        return (tokens, len(tokens)) if encode else (ret, len(tokens))
    
class AFormatterSimple():
    def __init__(self, tokenizer=None, systemAsUser = False):
        self.tokenizer = tokenizer
        self.systemAsUser = systemAsUser

    def __call__(self, prompt0, conversations, encode = True, assistTag = True):
        roleMap={'USER': 'User', 'ASSISTANT': 'Assistant', 'SYSTEM': 'System' if not self.systemAsUser else "User"}
        seps={'USER': "\n", 'ASSISTANT': "\n", 'SYSTEM': "\n"}

        ret = prompt0 + "\n" + "".join([f"### {roleMap[c['role']]}:\n{c['msg']}{seps[c['role']]}" for c in conversations]) + (f"### {roleMap['ASSISTANT']}:\n" if assistTag else "")
        #print("prompt: ", ret)
        tokens = self.tokenizer.encode(ret)
        return (tokens, len(tokens)) if encode else (ret, len(tokens))

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
        tokens = self.tokenizer.encode(ret)
        return (tokens, len(tokens)) if encode else (ret, len(tokens))

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
        tokens = self.tokenizer.encode(ret)
        return (tokens, len(tokens)) if encode else (ret, len(tokens))

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
        tokens = self.tokenizer.encode(ret)
        return (tokens, len(tokens)) if encode else (ret, len(tokens))

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
        tokens = self.tokenizer.encode(ret)
        return (tokens, len(tokens)) if encode else (ret, len(tokens))

class AFormatterCommandR():
    def __init__(self, tokenizer=None, systemAsUser = False):
        self.left={'USER': "<|START_OF_TURN_TOKEN|><|USER_TOKEN|>", 'ASSISTANT': "<|START_OF_TURN_TOKEN|><|CHATBOT_TOKEN|>", 'SYSTEM': "<|START_OF_TURN_TOKEN|><|SYSTEM_TOKEN|>"}
        self.right={'USER': "<|END_OF_TURN_TOKEN|>", 'ASSISTANT': "<|END_OF_TURN_TOKEN|>", 'SYSTEM': "<|END_OF_TURN_TOKEN|>"}
        self.tokenizer = tokenizer
        self.systemAsUser = systemAsUser
    
    def BuildMsg(self, role: str, msg: str):
        if self.systemAsUser and "SYSTEM" == role:
            role = "USER"
        return f"{self.left[role]}{msg}{self.right[role]}"
    
    def __call__(self, prompt0, conversations, encode = True, assistTag = True):
        ret = f"<BOS_TOKEN>{self.left['SYSTEM']}{prompt0}{self.right['SYSTEM']}" + "".join([self.BuildMsg(c["role"], c["msg"]) for c in conversations]) + (f"{self.left['ASSISTANT']}" if assistTag else "")
        #print("prompt: ", ret)
        tokens = self.tokenizer.encode(ret)
        return (tokens, len(tokens)) if encode else (ret, len(tokens))

class AFormatterGPT():
    def __init__(self, tokenizer=None, systemAsUser = False):
        self.systemAsUser = systemAsUser
        return
    
    def __call__(self, prompt0, conversations, encode = True, assistTag = True):
        roleMap = {"SYSTEM": "system" if not self.systemAsUser else "user", "USER": "user", "ASSISTANT": "assistant"}
        ret = [{"role": "system", "content": prompt0}] + [{"role": roleMap[c['role']], "content": c['msg']} for c in conversations]
        #print("prompt: ", ret)
        return ret, len(str(ret)) // 4

class AFormatterGPTVision():
    def __init__(self, tokenizer=None, systemAsUser = False):
        self.systemAsUser = systemAsUser
        return
    
    def ProcessAttachements(self, a):
        if "image" == a["type"]:
            return [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{a['content'].ToJson()['data']}"}}]
        elif "video" == a["type"]:
            numFrames = 10
            video = av.open(io.BytesIO(a['content'].data))
            frameIndices = [int(i * video.streams.video[0].frames / (numFrames - 1)) for i in range(numFrames)]
            ret = []
            for index in frameIndices:
                video.seek(index)
                frame = next(video.decode(video=0)).to_image()
                bytesDst = io.BytesIO()
                frame.save(bytesDst, format='JPEG')
                image = AImage(data=bytesDst.getvalue())
                ret.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image.Standardize().ToJson()['data']}"}})
            video.close()
            return ret
    
    def BuildMsg(self, role: str, msg: str, attachments: list):
        roleMap = {"SYSTEM": "system" if not self.systemAsUser else "user", "USER": "user", "ASSISTANT": "assistant"}
        return {"role": roleMap[role],
                "content": [{"type": "text", "text": msg}] +
                           sum([self.ProcessAttachements(a) for a in attachments if (a['type'] in ["image", "video"])], [])}
        
    def __call__(self, prompt0, conversations, encode = True, assistTag = True):
        ret = [{"role": "system", "content": [{"type": "text", "text": prompt0}]}] + [self.BuildMsg(c['role'], c['msg'], c['attachments']) for c in conversations]
        #print("prompt: ", ret)
        return ret, TokenEstimatorOAI(conversations)
    
class AFormatterClaudeVision():
    def __init__(self, tokenizer=None, systemAsUser = False):
        self.systemAsUser = systemAsUser
        return
    
    def ProcessAttachements(self, a):
        if "image" == a["type"]:
            return [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": a['content'].ToJson()['data']}}]
    
    def BuildMsg(self, role: str, msg: str, attachments: list):
        roleMap = {"SYSTEM": "system" if not self.systemAsUser else "user", "USER": "user", "ASSISTANT": "assistant"}
        return {"role": roleMap[role],
                "content": [{"type": "text", "text": msg}] +
                           sum([self.ProcessAttachements(a) for a in attachments if (a['type'] in ["image"])], [])}
        
    def __call__(self, prompt0, conversations, encode = True, assistTag = True):
        ret = [{"role": "system", "content": [{"type": "text", "text": prompt0}]}] + [self.BuildMsg(c['role'], c['msg'], c['attachments']) for c in conversations]
        #print("prompt: ", ret)
        return ret, TokenEstimatorOAI(conversations)
    

def CreateFormatter(formatterClsName: str, tokenizer, systemAsUser):
    formatterList = [obj for name, obj in inspect.getmembers(inspect.getmodule(inspect.currentframe())) if inspect.isclass(obj) and name.startswith("AFormatter")]
    for formatterCls in formatterList:
        if formatterClsName == formatterCls.__name__:
            return formatterCls(tokenizer = tokenizer, systemAsUser = systemAsUser)
    raise ValueError(f"{formatterClsName} is not a valid formatter class name.")