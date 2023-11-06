import os
import json
class AConfig():
    def __init__(self, maxMemory = {}, quantization = None, openaiGPTKey = None, temperature = 0.0, flashAttention2 = False):
        self.maxMemory = {}
        self.quantization = None
        self.openaiGPTKey = None
        self.temperature = temperature
        self.flashAttention2 = flashAttention2
        return

    def Load(self, configFile: str = "config.json") -> bool:
        if os.path.exists(configFile):
            with open(configFile, "r") as f:
                self.__dict__ = json.load(f)
            return True
        return False
    
    def Store(self, configFile: str = "config.json"):
        with open(configFile, "w") as f:
            json.dump(self.__dict__, f)
        return
    
    
config = AConfig()