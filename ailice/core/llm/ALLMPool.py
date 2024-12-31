import sys
import importlib.util

from ailice.common.AConfig import config

requirements = [x for x in ["torch", "transformers", "accelerate", "bitsandbytes"] if (None == importlib.util.find_spec(x))]
if 0 == len(requirements):
    from ailice.core.llm.AModelCausalLM import AModelCausalLM
from ailice.core.llm.AModelChatGPT import AModelChatGPT
from ailice.core.llm.AModelMistral import AModelMistral
from ailice.core.llm.AModelAnthropic import AModelAnthropic


class ALLMPool():
    def __init__(self):
        self.pool = dict()
        return
    
    def ParseID(self, id):
        split = id.find(":")
        return id[:split], id[split+1:]
    
    def Init(self, llmIDs: list[str]):
        MODEL_WRAPPER_MAP = {"AModelChatGPT": AModelChatGPT, "AModelMistral": AModelMistral, "AModelAnthropic": AModelAnthropic}
        if 0 == len(requirements):
            MODEL_WRAPPER_MAP["AModelCausalLM"] = AModelCausalLM
            MODEL_WRAPPER_MAP["AModelLLAMA"] = AModelCausalLM
        
        llmIDs = list(set([id for k,id in config.agentModelConfig.items()] + [id for id in llmIDs if "" != id])) if "" in llmIDs else llmIDs

        for id in llmIDs:
            modelType, modelName = self.ParseID(id)
            if (0 != len(requirements)) and (config.models[modelType]["modelWrapper"] in ["AModelCausalLM", "AModelLLAMA"]):
                print(f"The specified modelID {id} requires the installation of the following dependencies: {str(requirements)}. Please execute the following command to install: pip install {' '.join(requirements)}")
                sys.exit(0)
            if id not in self.pool:
                self.pool[id] = MODEL_WRAPPER_MAP[config.models[modelType]["modelWrapper"]](modelType=modelType, modelName=modelName)
        return
    
    def GetModel(self, modelID: str, agentType: str):
        if "" == modelID:
            if 'DEFAULT' not in config.agentModelConfig:
                print('You did not configure a default modelID (agentModelConfig["DEFAULT"]), which makes config.json invalid and unable to start. Please update your configuration.')
                sys.exit(0)
            modelID = config.agentModelConfig.get(agentType, config.agentModelConfig['DEFAULT'])
        return self.pool[modelID]