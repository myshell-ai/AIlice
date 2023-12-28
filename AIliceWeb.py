import time
import simplejson as json
import threading
from common.AConfig import config
from core.AProcessor import AProcessor
from llm.ALLMPool import llmPool
from utils.ALogger import ALogger
from common.ARemoteAccessors import clientPool, Browser, Arxiv, Google, Duckduckgo, Scripter
from AServices import StartServices

from common.APrompts import promptsManager
from prompts.APromptChat import APromptChat
from prompts.APromptMain import APromptMain
from prompts.APromptSearchEngine import APromptSearchEngine
from prompts.APromptRecurrent import APromptRecurrent
from prompts.APromptCoder import APromptCoder
from prompts.APromptModuleCoder import APromptModuleCoder
from prompts.APromptModuleLoader import APromptModuleLoader
from prompts.APromptCoderProxy import APromptCoderProxy
from prompts.APromptArticleDigest import APromptArticleDigest

import gradio as gr


def main(modelID: str, quantization: str, maxMemory: dict, prompt: str, temperature: float, flashAttention2: bool, contextWindowRatio: float, localExecution: bool, trace: str):
    config.Initialize(needOpenaiGPTKey = ("oai:" in modelID))
    config.quantization = quantization
    config.maxMemory = maxMemory
    config.temperature = temperature
    config.flashAttention2 = flashAttention2
    config.contextWindowRatio = contextWindowRatio
    config.localExecution = localExecution
    
    StartServices()
    clientPool.Init()

    for promptCls in [APromptChat, APromptMain, APromptSearchEngine, APromptRecurrent, APromptCoder, APromptModuleCoder, APromptModuleLoader, APromptCoderProxy, APromptArticleDigest]:
        promptsManager.RegisterPrompt(promptCls)
    
    llmPool.Init([modelID])
    
    logger = ALogger(speech=None)
    timestamp = str(time.time())
    processor = AProcessor(name="AIlice", modelID=modelID, promptName=prompt, outputCB=logger.Receiver, collection="ailice" + timestamp)
    processor.RegisterModules([Browser, Arxiv, Google, Duckduckgo, Scripter])
    def bot(text, history):
        if text is None:
            yield None
            return
        
        if "" != trace.strip():
            with open(trace + "/ailice-trace-" + timestamp + ".json", "w") as f:
                json.dump(processor.ToJson(), f)
        
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
    parser.add_argument('--localExecution',action='store_true', help="localExecution controls whether to execute code locally. The default is False, which means it is executed in docker container/VM/remote environment. Turning on this switch means that AI has full control over the local environment, which may lead to serious security risks. But you can place AIlice in In a virtual machine environment before turn on this switch. The advantage of this is that you can call visual tools more freely in automatic programming tasks.")
    parser.add_argument('--trace',type=str,default='', help="trace is used to specify the output directory for the execution history data. This option is empty by default, indicating that the execution history recording feature is not enabled.")
    kwargs = vars(parser.parse_args())
    main(**kwargs)