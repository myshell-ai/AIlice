import os
import json
import appdirs
from termcolor import colored

class AConfig():
    def __init__(self):
        self.maxMemory = {}
        self.quantization = None
        self.openaiGPTKey = None
        self.temperature = 0.0
        self.flashAttention2 = False
        self.speechOn = False
        self.contextWindowRatio = 0.6
        self.services = {
            "storage": {"cmd": "python3 -m ailice.modules.AStorageChroma --addr=ipc:///tmp/AIliceStorage.ipc", "addr": "ipc:///tmp/AIliceStorage.ipc"},
            "browser": {"cmd": "python3 -m ailice.modules.ABrowser --addr=ipc:///tmp/ABrowser.ipc", "addr": "ipc:///tmp/ABrowser.ipc"},
            "arxiv": {"cmd": "python3 -m ailice.modules.AArxiv --addr=ipc:///tmp/AArxiv.ipc", "addr": "ipc:///tmp/AArxiv.ipc"},
            "google": {"cmd": "python3 -m ailice.modules.AGoogle --addr=ipc:///tmp/AGoogle.ipc", "addr": "ipc:///tmp/AGoogle.ipc"},
            "duckduckgo": {"cmd": "python3 -m ailice.modules.ADuckDuckGo --addr=ipc:///tmp/ADuckDuckGo.ipc", "addr": "ipc:///tmp/ADuckDuckGo.ipc"},
            "scripter": {"cmd": "python3 -m ailice.modules.AScripter --addr=tcp://127.0.0.1:59000", "addr": "tcp://127.0.0.1:59000"},
            "speech": {"cmd": "python3 -m ailice.modules.ASpeech --addr=ipc:///tmp/ASpeech.ipc", "addr": "ipc:///tmp/ASpeech.ipc"},
        }
        return

    def Initialize(self, needOpenaiGPTKey = False):
        configFile = appdirs.user_config_dir("ailice", "Steven Lu")
        try:
            os.makedirs(configFile)
        except OSError as e:
            pass
        configFile += "/config.json"
        
        oldDict = self.Load(configFile)
        needUpdate = (set(oldDict.keys()) != set(self.__dict__))
        self.__dict__ = {k: oldDict[k] if k in oldDict else v for k,v in self.__dict__.items()}
        
        needUpdate = needUpdate or (needOpenaiGPTKey and (self.openaiGPTKey is None))
        
        if needUpdate:
            print("config.json need to be updated.")
            print(colored("********************** Initialize *****************************", "yellow"))
            if self.openaiGPTKey is None:
                key = input(colored("Your openai chatgpt key (press Enter if not): ", "green"))
                self.openaiGPTKey = key if 1 < len(key) else None
            self.Store(configFile)
            print(colored("********************** End of Initialization *****************************", "yellow"))
        print(f"config.json is located at {configFile}")

        if "2005" == self.services['scripter']['addr'][-4:]:
            print(colored(f"It seems that the script in your configuration file is configured on the 2005 port that was used in the old \
version, but this port has been abandoned and replaced with port 59000. This may cause AIlice to fail to start. \
Please change the configuration file and try again. The config file is located at: {configFile}", "red"))
        return

    def Load(self, configFile: str) -> dict:
        if os.path.exists(configFile):
            with open(configFile, "r") as f:
                return json.load(f)
        else:
            return dict()
    
    def Store(self, configFile: str):
        with open(configFile, "w") as f:
            json.dump(self.__dict__, f, indent=2)
        return
    
    
config = AConfig()