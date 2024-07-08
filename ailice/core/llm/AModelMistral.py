from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

from ailice.common.utils.ATextSpliter import sentences_split
from ailice.common.AConfig import config
from ailice.core.llm.AFormatter import CreateFormatter


class AModelMistral():
    def __init__(self, modelType: str, modelName: str):
        self.tokenizer = None
        self.modelType = modelType
        self.modelName = modelName
        self.client = MistralClient(api_key = config.models[modelType]["apikey"])

        modelCfg = config.models[modelType]["modelList"][modelName]
        self.formatter = CreateFormatter(modelCfg["formatter"], tokenizer = self.tokenizer, systemAsUser = modelCfg['systemAsUser'])
        self.contextWindow = modelCfg["contextWindow"]
        return
    
    def Generate(self, prompt: list[dict[str,str]], proc: callable, endchecker: callable, temperature: float) -> str:
        proc(txt='', action='open')
        currentPosition = 0
        text = ""
        for chunk in self.client.chat_stream(model=self.modelName,
                                             messages=[ChatMessage(**msg) for msg in prompt],
                                             temperature=temperature):
            text += (chunk.choices[0].delta.content or "")

            if endchecker(text):
                break
            
            sentences = [x for x in sentences_split(text[currentPosition:])]
            if (2 <= len(sentences)) and ("" != sentences[0].strip()):
                proc(txt=sentences[0], action='append')
                currentPosition += len(sentences[0])
        proc(txt=text[currentPosition:], action='close')
        return text