import os

from termcolor import colored
from mistralai import Mistral, models

from ailice.common.utils.ATextSpliter import sentences_split
from ailice.core.llm.AFormatter import CreateFormatter


class AModelMistral():
    def __init__(self, modelType: str, modelName: str, config):
        self.tokenizer = None
        self.modelType = modelType
        self.modelName = modelName
        self.config = config
        self.client = Mistral(api_key = config.models[modelType]["apikey"])

        self.modelCfg = config.models[modelType]["modelList"][modelName]
        self.formatter = CreateFormatter(self.modelCfg["formatter"], tokenizer = self.tokenizer, systemAsUser = self.modelCfg['systemAsUser'])
        self.contextWindow = self.modelCfg["contextWindow"]
        return
    
    def Generate(self, prompt: tuple[list[dict[str,str]],int], proc: callable, endchecker: callable, temperature: float, gasTank) -> str:
        currentPosition = 0
        text = ""
        extras = {}
        extras.update(self.modelCfg.get("args", {}))
        extras.update({"temperature": temperature} if None != temperature else {})
        try:
            gasTank.Consume(resourceType="Mistral/InputTokens", amount=prompt[1])
            for chunk in self.client.chat.stream(model=self.modelName,
                                                 messages=prompt[0],
                                                 timeout_ms=60000,
                                                 **extras):
                text += (chunk.data.choices[0].delta.content or "")

                if endchecker(text):
                    break
                
                sentences = [x for x in sentences_split(text[currentPosition:])]
                if (2 <= len(sentences)) and ("" != sentences[0].strip()):
                    gasTank.Consume(resourceType="Mistral/OutputTokens", amount=len(sentences[0]) // 4)
                    proc(txt=sentences[0])
                    currentPosition += len(sentences[0])
        except models.sdkerror.SDKError as e:
            if "Unauthorized" in e.body:
                msg = colored("The program encountered an authorization error. Please check your API key:", "yellow") + \
                    colored(f"\n\n{self.modelType}: ", "green") + colored(f"'{self.config.models[self.modelType]['apikey']}'\n\n", "blue") + \
                    colored("If it's incorrect, append '--resetApiKey' to the command parameters you are using to restart ailice and reset the API key.", "yellow")
                print('\n\n', msg)
                print('\n\nException:\n', str(e))
                os._exit(1)
            else:
                raise
        gasTank.Consume(resourceType="Mistral/OutputTokens", amount=len(text[currentPosition:]) // 4)
        proc(txt=text[currentPosition:])
        return text