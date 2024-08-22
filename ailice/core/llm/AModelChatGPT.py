import openai

from ailice.common.utils.ATextSpliter import sentences_split
from ailice.common.AConfig import config
from ailice.core.llm.AFormatter import CreateFormatter


class AModelChatGPT():
    def __init__(self, modelType: str, modelName: str):
        self.tokenizer = None
        self.modelType = modelType
        self.modelName = modelName
        self.client = openai.OpenAI(api_key = config.models[modelType]["apikey"],
                                    base_url = config.models[modelType]["baseURL"])

        modelCfg = config.models[modelType]["modelList"][modelName]
        self.formatter = CreateFormatter(modelCfg["formatter"], tokenizer = self.tokenizer, systemAsUser = modelCfg['systemAsUser'])
        self.contextWindow = modelCfg["contextWindow"]
        return
    
    def Generate(self, prompt: list[dict[str,str]], proc: callable, endchecker: callable, temperature: float) -> str:
        currentPosition = 0
        text = ""
        extras = {"max_tokens": 4096} if "vision" in self.modelName else {}
        if None != temperature:
            extras["temperature"] = temperature
        for chunk in self.client.chat.completions.create(model=self.modelName,
                                                         messages=prompt,
                                                         stream=True,
                                                         **extras):
            text += (chunk.choices[0].delta.content or "")

            if endchecker(text):
                break
            
            sentences = [x for x in sentences_split(text[currentPosition:])]
            if (2 <= len(sentences)) and ("" != sentences[0].strip()):
                proc(txt=sentences[0])
                currentPosition += len(sentences[0])
        proc(txt=text[currentPosition:])
        return text