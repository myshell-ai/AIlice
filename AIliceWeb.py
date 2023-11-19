import time
import threading
from common.AConfig import config
from core.AProcessor import AProcessor
from llm.ALLMPool import llmPool
from utils.ALogger import ALogger
from modules.ARemoteAccessors import Browser, Arxiv, Google, Duckduckgo, Scripter
from AServices import StartServices

from prompts.APrompts import promptsManager
from prompts.APromptChat import APromptChat
from prompts.APromptMain import APromptMain
from prompts.APromptSearchEngine import APromptSearchEngine
from prompts.APromptRecurrent import APromptRecurrent
from prompts.APromptCoder import APromptCoder
from prompts.APromptCoderProxy import APromptCoderProxy
from prompts.APromptArticleDigest import APromptArticleDigest

import gradio as gr


def main(modelID: str, quantization: str, maxMemory: dict, prompt: str, temperature: float, flashAttention2: bool):
    config.Initialize()
    config.quantization = quantization
    config.maxMemory = maxMemory
    config.temperature = temperature
    config.flashAttention2 = flashAttention2
    
    StartServices()

    for promptCls in [APromptChat, APromptMain, APromptSearchEngine, APromptRecurrent, APromptCoder, APromptCoderProxy, APromptArticleDigest]:
        promptsManager.RegisterPrompt(promptCls)
    
    llmPool.Init([modelID, "oai:gpt-3.5-turbo", "oai:gpt-4"])
    
    logger = ALogger(speech=None)
    processor = AProcessor(modelID=modelID, promptName=prompt, outputCB=logger.Receiver, collection="ailice" + str(time.time()))
    processor.RegisterModules([Browser, Arxiv, Google, Duckduckgo, Scripter])
    def bot(text, history):
        if text is None:
            yield None
            return
        threadLLM = threading.Thread(target=processor, args=(text,))
        threadLLM.start()
        ret = ""
        while True:
            channel, txt = logger.queue.get()
            if ">" == channel:
                threadLLM.join()
                return
            update = (channel + ":\r" + txt)
            ret += ("\r\r" + update)
            yield ret
    
    ui = gr.ChatInterface(fn=bot)
    ui.queue().launch()
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
    kwargs = vars(parser.parse_args())
    main(**kwargs)