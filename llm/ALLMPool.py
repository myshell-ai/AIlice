
from llm.AModelLLAMA import AModelLLAMA
from llm.AModelChatGPT import AModelChatGPT


class ALLMPool():
    def __init__(self):
        self.pool = dict()
        return
    
    def ParseID(self, id):
        split = id.find(":")
        return id[:split], id[split+1:]
    
    def Init(self, llmIDs: [str]):
        for id in llmIDs:
            locType, location = self.ParseID(id)
            
            if "hf" == locType:
                self.pool[id] = AModelLLAMA(modelLocation=location)
            elif "oai" == locType:
                self.pool[id] = AModelChatGPT(location)
            else:
                print("LLM id not in config list. id: ", id)
                continue
        return
    
    def GetModel(self, modelID: str):
        return self.pool[modelID]
    
llmPool = ALLMPool()