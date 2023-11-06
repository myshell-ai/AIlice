from termcolor import colored
from common.AConfig import config

def Initialize():
    if not config.Load("config.json"):
        print(colored("********************** Initialize *****************************", "yellow"))
        key = input(colored("Your openai chatgpt key (press Enter if not): ", "green"))
        config.openaiGPTKey = key if 1 < len(key) else None
        config.Store("config.json")
        print(colored("********************** End of Initialization *****************************", "yellow"))
    return