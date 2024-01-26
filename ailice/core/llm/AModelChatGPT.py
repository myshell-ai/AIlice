import openai

from ailice.common.utils.ATextSpliter import sentences_split
from ailice.common.AConfig import config
from ailice.core.llm.AFormatter import AFormatterGPT


class AModelChatGPT():
    def __init__(self, modelType: str, modelName: str):
        self.tokenizer = None
        self.modelType = modelType
        self.modelName = modelName
        self.client = openai.OpenAI(api_key = config.models[modelType]["apikey"],
                                    base_url = config.models[modelType]["baseURL"])

        self.formatter = AFormatterGPT(tokenizer = self.tokenizer, systemAsUser = False)
        self.contextWindow = config.models[modelType]["modelList"][modelName]["contextWindow"]
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