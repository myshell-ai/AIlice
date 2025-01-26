import os
import anthropic

from termcolor import colored
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

        self.modelCfg = config.models[modelType]["modelList"][modelName]
        self.formatter = CreateFormatter(self.modelCfg["formatter"], tokenizer = self.tokenizer, systemAsUser = self.modelCfg['systemAsUser'])
        self.contextWindow = self.modelCfg["contextWindow"]
        return
    
    def Generate(self, prompt: list[dict[str,str]], proc: callable, endchecker: callable, temperature: float) -> str:
        currentPosition = 0
        text = ""
        extras = {}
        extras.update(self.modelCfg.get("args", {}))
        extras.update({"temperature": temperature} if None != temperature else {})
        try:
            with self.client.messages.stream(model=self.modelName,
                                            max_tokens=4096,
                                            system=prompt[0]["content"],
                                            messages=prompt[1:],
                                            **extras) as stream:
                for delta in stream.text_stream:
                    text += delta

                    if endchecker(text):
                        break
                    
                    sentences = [x for x in sentences_split(text[currentPosition:])]
                    if (2 <= len(sentences)) and ("" != sentences[0].strip()):
                        proc(txt=sentences[0])
                        currentPosition += len(sentences[0])
        except anthropic.AuthenticationError as e:
            msg = colored("The program encountered an authorization error. Please check your API key:", "yellow") + \
                  colored(f"\n\n{self.modelType}: ", "green") + colored(f"'{config.models[self.modelType]['apikey']}'\n\n", "blue") + \
                  colored("If it's incorrect, append '--resetApiKey' to the command parameters you are using to restart ailice and reset the API key.", "yellow")
            print('\n\n', msg)
            print('\n\nException:\n', str(e))
            os._exit(1)
        proc(txt=text[currentPosition:])
        return text