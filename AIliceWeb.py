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


def main(modelID: str, quantization: str, maxMemory: dict, prompt: str, temperature: float, flashAttention2: bool, contextWindowRatio: float):
    config.Initialize()
    config.quantization = quantization
    config.maxMemory = maxMemory
    config.temperature = temperature
    config.flashAttention2 = flashAttention2
    config.contextWindowRatio = contextWindowRatio
    
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
    parser.add_argument('--modelID',type=str,default='hf:Open-Orca/Mistral-7B-OpenOrca', help="modelID specifies the model. The currently supported models can be seen in llm/ALLMPool.py, just copy it directly. We will implement a simpler model specification method in the future.")
    parser.add_argument('--quantization',type=str,default='', help="quantization is the quantization option, you can choose 4bit or 8bit. The default is not quantized.")
    parser.add_argument('--maxMemory',type=dict,default=None, help='maxMemory is the memory video memory capacity constraint, the default is not set, the format when set is like "{0:"23GiB", 1:"24GiB", "cpu": "64GiB"}".')
    parser.add_argument('--prompt',type=str,default='main', help="prompt specifies the prompt to be executed, which is the type of agent. The default is 'main', this agent will decide to call the appropriate agent type according to your needs. You can also specify a special type of agent and interact with it directly.")
    parser.add_argument('--temperature',type=float,default=0.0, help="temperature sets the temperature parameter of LLM reasoning, the default is zero.")
    parser.add_argument('--flashAttention2',action='store_true', help="flashAttention2 is the switch to enable flash attention 2 to speed up inference. It may have a certain impact on output quality.")
    parser.add_argument('--contextWindowRatio',type=float,default=0.6, help="contextWindowRatio is a user-specified proportion coefficient, which determines the proportion of the upper limit of the prompt length constructed during inference to the LLM context window in some cases. The default value is 0.6.")
    kwargs = vars(parser.parse_args())
    main(**kwargs)