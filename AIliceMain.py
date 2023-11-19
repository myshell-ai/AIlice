import time
from termcolor import colored

from common.AConfig import config
from core.AProcessor import AProcessor
from llm.ALLMPool import llmPool
from utils.ALogger import ALogger
from modules.ARemoteAccessors import makeClient, Browser, Arxiv, Google, Duckduckgo, Speech, Scripter
from AServices import StartServices

from prompts.APrompts import promptsManager
from prompts.APromptChat import APromptChat
from prompts.APromptMain import APromptMain
from prompts.APromptSearchEngine import APromptSearchEngine
from prompts.APromptRecurrent import APromptRecurrent
from prompts.APromptCoder import APromptCoder
from prompts.APromptCoderProxy import APromptCoderProxy
from prompts.APromptArticleDigest import APromptArticleDigest


def GetInput(speech) -> str:
    if config.speechOn:
        print(colored("USER: ", "green"), end="", flush=True)
        inp = speech.GetAudio()
        print(inp, end="", flush=True)
        print("")
    else:
        inp = input(colored("USER: ", "green"))
    return inp

def main(modelID: str, quantization: str, maxMemory: dict, prompt: str, temperature: float, flashAttention2: bool, speechOn: bool, ttsDevice: str, sttDevice: str):
    config.Initialize()
    config.quantization = quantization
    config.maxMemory = maxMemory
    config.temperature = temperature
    config.flashAttention2 = flashAttention2
    config.speechOn = speechOn
    
    StartServices()

    if speechOn:
        speech = makeClient(Speech)
        if (ttsDevice not in {'cpu','cuda'}) or (sttDevice not in {'cpu','cuda'}):
            print("the value of ttsDevice and sttDevice should be one of cpu or cuda, the default is cpu.")
            exit(-1)
        else:
            speech.SetDevices({"tts": ttsDevice, "stt": sttDevice})
    else:
        speech = None
    
    for promptCls in [APromptChat, APromptMain, APromptSearchEngine, APromptRecurrent, APromptCoder, APromptCoderProxy, APromptArticleDigest]:
        promptsManager.RegisterPrompt(promptCls)
    
    llmPool.Init([modelID, "oai:gpt-3.5-turbo", "oai:gpt-4"])
    
    logger = ALogger(speech=speech)
    processor = AProcessor(modelID=modelID, promptName=prompt, outputCB=logger.Receiver, collection="ailice" + str(time.time()))
    processor.RegisterModules([Browser, Arxiv, Google, Duckduckgo, Scripter] + ([Speech] if config.speechOn else []))
    while True:
        inpt = GetInput(speech)
        processor(inpt)
    return

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--modelID',type=str,default='hf:Open-Orca/Mistral-7B-OpenOrca')
    parser.add_argument('--quantization',type=str,default='')
    parser.add_argument('--maxMemory',type=dict,default=None)
    parser.add_argument('--prompt',type=str,default='main')
    parser.add_argument('--temperature',type=float,default=0.0)
    parser.add_argument('--flashAttention2',action='store_true')
    parser.add_argument('--speechOn',action='store_true')
    parser.add_argument('--ttsDevice',type=str,default='cpu',help="cpu or cuda, the default is cpu.")
    parser.add_argument('--sttDevice',type=str,default='cpu',help="cpu or cuda, the default is cpu.")
    kwargs = vars(parser.parse_args())
    main(**kwargs)