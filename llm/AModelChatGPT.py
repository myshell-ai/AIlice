import openai

from utils.ATextSpliter import sentences_split
from common.AConfig import config


class AModelChatGPT():
    def __init__(self, modelName: str):
        openai.api_key = config.openaiGPTKey
        self.tokenizer = None
        self.modelName = modelName
        return
    
    def Generate(self, prompt: list[dict[str,str]], proc: callable, endchecker: callable, temperature: float = 0.2) -> str:
        proc(channel='ASSISTANT', txt='', action='open')
        currentPosition = 0
        text = ""
        for chunk in openai.ChatCompletion.create(model=self.modelName,
                                                  messages=prompt,
                                                  temperature=temperature,
                                                  stream=True):
            content = chunk["choices"][0].get("delta", {}).get("content")
            if content is not None:
                text += content

            if endchecker(text):
                break
            
            sentences = [x for x in sentences_split(text[currentPosition:])]
            if (2 <= len(sentences)) and ("" != sentences[0].strip()):
                proc(channel='ASSISTANT', txt=sentences[0], action='append')
                currentPosition += len(sentences[0])
        proc(channel='ASSISTANT', txt=text[currentPosition:], action='close')
        return text