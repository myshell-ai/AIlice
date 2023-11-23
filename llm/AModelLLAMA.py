import torch
from termcolor import colored
import transformers
from peft import PeftConfig, PeftModel

from common.AConfig import config
from utils.ATextSpliter import sentences_split
from llm.ALLMMeta import ALLMMeta


class AModelLLAMA():
    def __init__(self, modelLocation: str):
        self.tokenizer = None
        self.model = None
        self.LoadModel(modelLocation)
        
        modelID = "hf:" + modelLocation
        if modelID not in ALLMMeta:
            print(f"LLM {modelID} not supported yet.")
            exit(-1)
        self.formatter = ALLMMeta[modelID]['formatter'](tokenizer = self.tokenizer, systemAsUser = True)
        self.contextWindow = ALLMMeta[modelID]['contextWindow']
        return

    def LoadModel(self, modelLocation: str):
        quantizationConfig = transformers.BitsAndBytesConfig(llm_int4_enable_fp32_cpu_offload=True)
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(modelLocation, use_fast=False, legacy=False, force_download=False, resume_download=True)
        self.model = transformers.AutoModelForCausalLM.from_pretrained(modelLocation,
                                                    device_map="auto",
                                                    low_cpu_mem_usage=True,
                                                    load_in_4bit=("4bit" == config.quantization),
                                                    load_in_8bit=("8bit" == config.quantization),
                                                    use_flash_attention_2=config.flashAttention2,
                                                    #quantization_config=quantizationConfig,
                                                    max_memory=config.maxMemory,
                                                    offload_folder="offload",
                                                    force_download=False, resume_download=True
                                                    )
        return

    def LoadModel_LoRA(self, modelLocation: str):
        config = PeftConfig.from_pretrained(modelLocation)
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(config.base_model_name_or_path, use_fast=False)
        self.model = transformers.AutoModelForCausalLM.from_pretrained(config.base_model_name_or_path,
                                                    device_map="auto",
                                                    low_cpu_mem_usage=True,
                                                    load_in_4bit=("4bit" == config.quantization),
                                                    load_in_8bit=("8bit" == config.quantization),
                                                    max_memory=config.maxMemory,
                                                    offload_folder="offload"
                                                    )
        self.model = PeftModel.from_pretrained(self.model, modelLocation)
        return
    
    def Generate(self, prompt: str, proc: callable, endchecker: callable, temperature: float = 0.2) -> str:
        proc(channel='ASSISTANT', txt='', action='open')

        predictedIDs = torch.tensor([prompt]).cuda() #(b, seq)

        generatedIDs = None
        pastKeyValues = None
        currentPosition = 0
        text = ""
        for _ in range(4096):
            with torch.no_grad():
                outputs = self.model(
                    input_ids=predictedIDs, 
                    past_key_values=pastKeyValues, 
                    use_cache=True
                )
            
            logits = outputs.logits #(b, seq, vocabulary)
            pastKeyValues = outputs.past_key_values

            if temperature > 1e-9:
                scaledLogits = logits / temperature
                probs = torch.nn.functional.softmax(scaledLogits, dim=-1)
                predictedIDs = torch.multinomial(probs[:, -1, :], 1)
            else:
                predictedIDs = torch.argmax(logits[..., -1, :], dim=-1, keepdim=True) #(b, 1)
            
            generatedIDs = predictedIDs if None == generatedIDs else torch.cat((generatedIDs, predictedIDs), dim=-1)
            text = self.tokenizer.decode(generatedIDs[0].cpu().numpy(), skip_special_tokens=True)
            if (predictedIDs.item() == self.tokenizer.eos_token_id) or endchecker(text):
                break

            sentences = [x for x in sentences_split(text[currentPosition:])]
            if (2 <= len(sentences)) and ("" != sentences[0].strip()):
                proc(channel='ASSISTANT', txt=sentences[0], action='append')
                currentPosition += len(sentences[0])

        proc(channel='ASSISTANT', txt=text[currentPosition:], action='close')
        return text