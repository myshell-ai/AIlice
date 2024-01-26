from ailice.common.AConfig import config
from ailice.core.llm.AModelLLAMA import AModelLLAMA
from ailice.core.llm.AModelChatGPT import AModelChatGPT


class ALLMPool():
    def __init__(self):
        self.pool = dict()
        return
    
    def ParseID(self, id):
        split = id.find(":")
        return id[:split], id[split+1:]
    
    def Init(self, llmIDs: [str]):
        MODEL_WRAPPER_MAP = {"AModelLLAMA": AModelLLAMA, "AModelChatGPT": AModelChatGPT}
        for id in llmIDs:
            modelType, modelName = self.ParseID(id)
            if modelType in ["hf", "file", "peft"]:
                self.pool[id] = AModelLLAMA(modelType=modelType, modelName=modelName)
            else:
                self.pool[id] = MODEL_WRAPPER_MAP[config.models[modelType]["modelWrapper"]](modelType=modelType, modelName=modelName)
        return
    
    def GetModel(self, modelID: str):
        return self.pool[modelID]
    
llmPool = ALLMPool()