
from llm.AModelLLAMA import AModelLLAMA
from llm.AModelChatGPT import AModelChatGPT
from llm.AFormatter import AFormatterSimple,AFormatterLLAMA2,AFormatterVicuna,AFormatterChatML,AFormatterGPT,AFormatterAMAZON, AFormatterZephyr


class ALLMPool():
    def __init__(self):
        self.pool = dict()
        self.configs={"hf:meta-llama/Llama-2-13b-chat-hf": {"formatter": AFormatterLLAMA2},
                      "hf:meta-llama/Llama-2-70b-chat-hf": {"formatter": AFormatterLLAMA2},
                      "hf:upstage/llama-30b-instruct-2048": {"formatter": AFormatterSimple},
                      "hf:lmsys/vicuna-33b-v1.3": {"formatter": AFormatterVicuna},
                      "hf:Phind/Phind-CodeLlama-34B-v2": {"formatter": AFormatterSimple},
                      "hf:Xwin-LM/Xwin-LM-70B-V0.1": {"formatter": AFormatterVicuna},
                      "hf:Xwin-LM/Xwin-LM-13B-V0.1": {"formatter": AFormatterVicuna},
                      "hf:mistralai/Mistral-7B-Instruct-v0.1": {"formatter": AFormatterLLAMA2},
                      "hf:Open-Orca/Mistral-7B-OpenOrca": {"formatter": AFormatterChatML},
                      "hf:amazon/MistralLite": {"formatter": AFormatterAMAZON},
                      "hf:HuggingFaceH4/zephyr-7b-beta": {"formatter": AFormatterZephyr},
                      "hf:THUDM/agentlm-13b": {"formatter": AFormatterLLAMA2}}
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
    
    def GetFormatter(self, modelID: str):
        if modelID in self.configs:
            Formatter = self.configs[modelID]['formatter']
        elif "oai:gpt" in modelID:
            Formatter = AFormatterGPT
        else:
            print(f"LLM {modelID} not supported yet.")
            exit(-1)
        return Formatter(tokenizer = self.pool[modelID].tokenizer, systemAsUser = True)
    
llmPool = ALLMPool()