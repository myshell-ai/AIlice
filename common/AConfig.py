import os
import json
from termcolor import colored

class AConfig():
    def __init__(self, maxMemory = {}, quantization = None, openaiGPTKey = None, temperature = 0.0, flashAttention2 = False, speechOn = False):
        self.maxMemory = {}
        self.quantization = None
        self.openaiGPTKey = None
        self.temperature = temperature
        self.flashAttention2 = flashAttention2
        self.speechOn = False
        return

    def Initialize(self):
        oldDict = self.Load("config.json")
        needUpdate = (set(oldDict.keys()) != set(self.__dict__))
        self.__dict__ = {k: oldDict[k] if k in oldDict else v for k,v in self.__dict__.items()}
        
        if needUpdate:
            print("config.json does not match the code version, an update operation will be performed.")
            print(colored("********************** Initialize *****************************", "yellow"))
            if self.openaiGPTKey is None:
                key = input(colored("Your openai chatgpt key (press Enter if not): ", "green"))
                self.openaiGPTKey = key if 1 < len(key) else None
            self.Store("config.json")
            print(colored("********************** End of Initialization *****************************", "yellow"))
        return

    def Load(self, configFile: str = "config.json") -> dict:
        if os.path.exists(configFile):
            with open(configFile, "r") as f:
                return json.load(f)
        else:
            return dict()
    
    def Store(self, configFile: str = "config.json"):
        with open(configFile, "w") as f:
            json.dump(self.__dict__, f)
        return
    
    
config = AConfig()