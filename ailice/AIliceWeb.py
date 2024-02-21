import time
import os
import io
from PIL import Image
import simplejson as json
import traceback
from termcolor import colored

import threading
from ailice.common.AConfig import config
from ailice.core.AProcessor import AProcessor
from ailice.core.llm.ALLMPool import llmPool
from ailice.common.utils.ALogger import ALogger
from ailice.common.utils.AFileUtils import serialize
from ailice.common.ADataType import AImage
from ailice.common.ARemoteAccessors import clientPool
from ailice.AServices import StartServices, TerminateSubprocess

from ailice.common.APrompts import promptsManager
from ailice.prompts.APromptChat import APromptChat
from ailice.prompts.APromptMain import APromptMain
from ailice.prompts.APromptSearchEngine import APromptSearchEngine
from ailice.prompts.APromptResearcher import APromptResearcher
from ailice.prompts.APromptCoder import APromptCoder
from ailice.prompts.APromptModuleCoder import APromptModuleCoder
from ailice.prompts.APromptModuleLoader import APromptModuleLoader
from ailice.prompts.APromptCoderProxy import APromptCoderProxy
from ailice.prompts.APromptArticleDigest import APromptArticleDigest

import gradio as gr

def mainLoop(modelID: str, quantization: str, maxMemory: dict, prompt: str, temperature: float, flashAttention2: bool, contextWindowRatio: float, trace: str):
    config.Initialize(needOpenaiGPTKey = ("oai:" in modelID))
    config.quantization = quantization
    config.maxMemory = maxMemory
    config.temperature = temperature
    config.flashAttention2 = flashAttention2
    config.contextWindowRatio = contextWindowRatio
    
    print(colored("In order to simplify installation and usage, we have set local execution as the default behavior, which means AI has complete control over the local environment. \
To prevent irreversible losses due to potential AI errors, you may consider one of the following two methods: the first one, run AIlice in a virtual machine; the second one, install Docker, \
use the provided Dockerfile to build an image and container, and modify the relevant configurations in config.json. For detailed instructions, please refer to the documentation.", "red"))

    StartServices()
    clientPool.Init()

    for promptCls in [APromptChat, APromptMain, APromptSearchEngine, APromptResearcher, APromptCoder, APromptModuleCoder, APromptModuleLoader, APromptCoderProxy, APromptArticleDigest]:
        promptsManager.RegisterPrompt(promptCls)
    
    llmPool.Init([modelID])
    
    logger = ALogger(speech=None)
    timestamp = str(time.time())
    processor = AProcessor(name="AIlice", modelID=modelID, promptName=prompt, outputCB=logger.Receiver, collection="ailice" + timestamp)
    processor.RegisterModules([config.services['browser']['addr'],
                               config.services['arxiv']['addr'],
                               config.services['google']['addr'],
                               config.services['duckduckgo']['addr'],
                               config.services['scripter']['addr']])
    def bot(history):
        if "" != trace.strip():
            with open(trace + "/ailice-trace-" + timestamp + ".json", "w") as f:
                json.dump(processor.ToJson(), f, indent=2, default=serialize)
        
        if str != type(history[-1][0]):
            msg = f'Please observe this image. <AImageLocation|"{history[-1][0][0]}"|AImageLocation>'
        else:
            msg = history[-1][0]
        threadLLM = threading.Thread(target=processor, args=(msg,))
        threadLLM.start()
        history[-1][1] = ""
        while True:
            channel, txt = logger.queue.get()
            if ">" == channel:
                threadLLM.join()
                return
            update = (channel + ":\r" + txt)
            history[-1][1] += ("\r\r" + update)
            yield history
    
    def add_text(history, text):
        history = history + [(text, None)]
        return history, gr.Textbox(value="", interactive=False)

    def add_file(history, file):
        history = history + [((file.name,), None)]
        return history

    with gr.Blocks() as demo:
        chatbot = gr.Chatbot(
            [],
            elem_id="chatbot",
            bubble_full_width=False,
            line_breaks=False,
            avatar_images=(None, (os.path.join(os.path.dirname(__file__), f"../AIlice.png"))),
        )

        with gr.Row():
            txt = gr.Textbox(
                scale=4,
                show_label=False,
                placeholder="Enter text and press enter, or upload an image",
                container=False,
            )
            btn = gr.UploadButton("📁", file_types=["image"])

        txt_msg = txt.submit(add_text, [chatbot, txt], [chatbot, txt], queue=False).then(
            bot, chatbot, chatbot, api_name="bot_response"
        )
        txt_msg.then(lambda: gr.Textbox(interactive=True), None, [txt], queue=False)
        file_msg = btn.upload(add_file, [chatbot, btn], [chatbot], queue=False).then(
            bot, chatbot, chatbot
        )

    demo.queue()
    demo.launch()
    return

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--modelID',type=str,default='hf:Open-Orca/Mistral-7B-OpenOrca', help="modelID specifies the model. The currently supported models can be seen in llm/ALLMPool.py, just copy it directly. We will implement a simpler model specification method in the future.")
    parser.add_argument('--quantization',type=str,default='', help="quantization is the quantization option, you can choose 4bit or 8bit. The default is not quantized.")
    parser.add_argument('--maxMemory',type=dict,default=None, help='maxMemory is the memory video memory capacity constraint, the default is not set, the format when set is like "{0:"23GiB", 1:"24GiB", "cpu": "64GiB"}".')
    parser.add_argument('--prompt',type=str,default='main', help="prompt specifies the prompt to be executed, which is the type of agent. The default is 'main', this agent will decide to call the appropriate agent type according to your needs. You can also specify a special type of agent and interact with it directly.")
    parser.add_argument('--temperature',type=float,default=0.0, help="temperature sets the temperature parameter of LLM reasoning, the default is zero.")
    parser.add_argument('--flashAttention2',action='store_true', help="flashAttention2 is the switch to enable flash attention 2 to speed up inference. It may have a certain impact on output quality.")
    parser.add_argument('--contextWindowRatio',type=float,default=0.6, help="contextWindowRatio is a user-specified proportion coefficient, which determines the proportion of the upper limit of the prompt length constructed during inference to the LLM context window in some cases. The default value is 0.6.")
    parser.add_argument('--trace',type=str,default='', help="trace is used to specify the output directory for the execution history data. This option is empty by default, indicating that the execution history recording feature is not enabled.")
    kwargs = vars(parser.parse_args())

    try:
        mainLoop(**kwargs)
    except Exception as e:
        print(f"Encountered an exception, AIlice is exiting: {str(e)}")
        traceback.print_tb(e.__traceback__)
        TerminateSubprocess()
        raise

if __name__ == '__main__':
    main()