import anthropic

from ailice.common.utils.ATextSpliter import sentences_split
from ailice.common.AConfig import config
from ailice.core.llm.AFormatter import CreateFormatter


class AModelAnthropic():
    def __init__(self, modelType: str, modelName: str):
        self.tokenizer = None
        self.modelType = modelType
        self.modelName = modelName
        self.client = anthropic.Anthropic(api_key = config.models[modelType]["apikey"],
                                          base_url = config.models[modelType]["baseURL"])

        modelCfg = config.models[modelType]["modelList"][modelName]
        self.formatter = CreateFormatter(modelCfg["formatter"], tokenizer = self.tokenizer, systemAsUser = modelCfg['systemAsUser'])
        self.contextWindow = modelCfg["contextWindow"]
        return
    
    def Generate(self, prompt: list[dict[str,str]], proc: callable, endchecker: callable, temperature: float = 0.2) -> str:
        proc(txt='', action='open')
        currentPosition = 0
        text = ""
        with self.client.messages.stream(model=self.modelName,
                                         max_tokens=4096,
                                         system=prompt[0]["content"],
                                         messages=prompt[1:],
                                         temperature=temperature) as stream:
            for delta in stream.text_stream:
                text += delta

                if endchecker(text):
                    break
                
                sentences = [x for x in sentences_split(text[currentPosition:])]
                if (2 <= len(sentences)) and ("" != sentences[0].strip()):
                    proc(txt=sentences[0], action='append')
                    currentPosition += len(sentences[0])
        proc(txt=text[currentPosition:], action='close')
        return text