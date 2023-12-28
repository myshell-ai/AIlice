import openai

from common.utils.ATextSpliter import sentences_split
from common.AConfig import config
from llm.AFormatter import AFormatterGPT


class AModelChatGPT():
    def __init__(self, modelName: str):
        self.tokenizer = None
        self.modelName = modelName
        self.client = openai.OpenAI(api_key = config.openaiGPTKey)

        self.formatter = AFormatterGPT(tokenizer = self.tokenizer, systemAsUser = True)
        self.contextWindow = {
            "gpt-4-1106-preview": 128000,
            "gpt-4-vision-preview": 128000,
            "gpt-4": 8192,
            "gpt-4-32k": 32768,
            "gpt-4-0613": 8192,
            "gpt-4-32k-0613": 32768,
            "gpt-4-0314": 8192,
            "gpt-4-32k-0314": 32768
        }.get(modelName, 8192)
        return
    
    def Generate(self, prompt: list[dict[str,str]], proc: callable, endchecker: callable, temperature: float = 0.2) -> str:
        proc(txt='', action='open')
        currentPosition = 0
        text = ""
        for chunk in self.client.chat.completions.create(model=self.modelName,
                                                         messages=prompt,
                                                         temperature=temperature,
                                                         stream=True):
            text += (chunk.choices[0].delta.content or "")

            if endchecker(text):
                break
            
            sentences = [x for x in sentences_split(text[currentPosition:])]
            if (2 <= len(sentences)) and ("" != sentences[0].strip()):
                proc(txt=sentences[0], action='append')
                currentPosition += len(sentences[0])
        proc(txt=text[currentPosition:], action='close')
        return text