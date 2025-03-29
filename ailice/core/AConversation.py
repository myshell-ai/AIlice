import re
import time
import random
import concurrent.futures

from typing import Any
from ailice.common.ADataType import typeInfo, GuessMediaType, ToJson, FromJson, AImageLocation, AVideoLocation


class AConversations():
    def __init__(self, proxy):
        self.proxy = proxy
        self.conversations: list[dict] = []
        return
    
    def Add(self, role: str, msg: str, env: dict[str,Any], entry: bool = False):
        msg = "<EMPTY MSG>" if ("" == msg) else msg
        record = {"role": role, "time": time.time(), "entry": entry, "msg": msg, "attachments": []}
        
        if role in ["USER", "SYSTEM"]:
            matches = re.findall(r"```(\w*)\n([\s\S]*?)```", msg)
            vars = []
            for language, code in matches:
                varName = f"code_{language}_{str(random.randint(0,10000))}"
                env[varName] = code
                vars.append(varName)
            if 0 < len(vars):
                record['msg'] += f"\nSystem notification: The code snippets within the triple backticks in this message have been saved as variables, in accordance with their order in the text, the variable names are as follows: {vars}\n"
            
            matches = [m for m in re.findall(r"(!\[([^\]]*?)\]\((.*?)\)(?:<([a-zA-Z0-9_\-&]+)>)?)", msg)]
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(self.ProcessMultimodalTags, m, param, label, env) for m, txt, param, label in matches]
                for future, match in zip(concurrent.futures.as_completed(futures), matches):
                    try:
                        m, txt, param, label = match
                        result = future.result()
                        if isinstance(result, Exception):
                            msgNew = msg.replace(m, f"{m}\n(System notification: Unable to get multimodal content: {e})")
                            record["msg"] = msgNew
                        elif None != result:
                            record["attachments"].append(result)
                    except Exception as e:
                        record["msg"] += f"\nSystem notification: Exception encountered while processing multimodal tags: {str(e)}"

        self.conversations.append(record)
        return
    
    def ProcessMultimodalTags(self, m, param, label, env):
        if ("&" == label):
            if ("" == param) or (param not in env):
                raise ValueError(f"variable name ({param}) not defined.")
            return {"type": typeInfo[type(env[param])]['modal'], "tag": m, "content": env[param].Standardize()}
        elif "" != label:
            targetType = [t for t in typeInfo if (t.__name__ == label)]
            if 0 == len(targetType):
                raise ValueError(f"modal type: {label} not found. supported modal type list: {[str(t.__name__) for t in typeInfo]}. please check your input.")
            else:
                return {"type": typeInfo[targetType[0]]['modal'], "tag": m, "content": targetType[0](param).Standardize()}
        else:
            mimeType = GuessMediaType(param)
            if "image" in mimeType:
                return {"type": "image", "tag": m, "content": AImageLocation(urlOrPath=param).Standardize(self.proxy)}
            elif "video" in mimeType:
                return {"type": "video", "tag": m, "content": AVideoLocation(urlOrPath=param).Standardize(self.proxy)}
            return
    
    def LatestEntry(self):
        for i in range(len(self.conversations)):
            if self.conversations[-i-1]['entry']:
                break
        return (-(i+1)//2) if ('ASSISTANT' == self.conversations[-1]['role']) else ((-i-2)//2)
    
    def GetConversations(self, frm=0):
        s = (2*frm) if (frm >= 0) or ('ASSISTANT' == self.conversations[-1]['role']) else (2*frm+1)
        return self.conversations[s:]
    
    def __len__(self):
        return (len(self.conversations)+1) // 2
    
    def FromJson(self, data):
        def AddRecord(role, time, entry, msg, attachments):
            self.conversations.append({'role': role,
                                       'time': time,
                                       'entry': entry,
                                       'msg': msg,
                                       'attachments': attachments})
        for i in range(0, len(data)):
            d = data[i]
            if i > 0:
                assert not ({d['role'], data[i-1]['role']} <= {"ASSISTANT"}), f"Consecutive ASSISTANT messages were found in conversations. {str(d)}, {str(data[i-1])}"
                if {d['role'], data[i-1]['role']} <= {"USER", "SYSTEM"}:
                    AddRecord('ASSISTANT', None, False, '<EMPTY MSG>', [])
            AddRecord(d['role'], d.get('time', None), d.get('entry', None), d['msg'] if '' != d['msg'] else '<EMPTY MSG>', [{'type': a['type'], 'tag': a.get('tag', None), 'content': FromJson(a['content'])} for a in d['attachments']])
        if (len(data) > 0) and (data[-1]['role'] in ['USER', 'SYSTEM']):
            AddRecord('ASSISTANT', None, False, '<EMPTY MSG>', [])
        return
    
    def ToJson(self) -> str:
        return [{'role': record['role'],
                 'time': record['time'],
                 'entry': record['entry'],
                 'msg': record['msg'],
                 'attachments': [{'type': a['type'],
                                  'tag': a['tag'],
                                  'content': ToJson(a['content'])} for a in record['attachments']]} for record in self.conversations]