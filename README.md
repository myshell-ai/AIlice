
![AIlice](./AIlice.png)

# Why create another agent?
This is due to two reasons. 

First, we need **a simple framework that is easy to understand and sufficiently controllable** to test various new ideas about agents. This requires building a fully functional agent framework within a few thousand lines of code.

Second, despite the current strength of OpenAI's products, we place hope in the open-source community for the future. This is not only because of the idealistic desire to break the monopoly on AGI but also for technical reasons. We anticipate that **future agents will run for extended periods on local machines, performing various complex tasks from local data analysis to information investigations on the internet**. Many of these tasks require good reasoning abilities rather than vast amounts of knowledge. We hope that in the future, a lightweight, high-reasoning-capacity open-source LLM (Lightweight Language Model) will emerge to realize this ideal.


# Introduction

AIlice is a lightweight AI Agent under development, which also serves as a simple development framework for quickly building and experimenting with various AI Agent ideas.
Her features are briefly listed as follows:

- **Natural multi-Agent invocation and interaction mechanism.**
- **Parsing LLM output in the most flexible way possible, supporting more varied function call mechanisms.**
- **Support for various open-source LLMs and commercial models like gpt-4.**
- **Support for peripheral modules such as web page, pdf browsing, searching, bash, Python code execution, voice dialogue, etc. which run as RPC services in a separable runtime environment.**


# COOL things we can do
You can try the following inputs and interact with AIlice to see if you can produce interesting results (the results will vary due to changes in the development process and differences in the model).

- **"Please search the internet for 100 tutorials in various branches of physics and report the URLs for the PDF files you find. There is no need to verify these URLs, we only need a rough collection for now."**

- **"Please conduct an investigation on open-source PDF OCR tools, with a focus on those capable of recognizing mathematical formulas and converting them into LaTeX code. Consolidate the findings into a report."**

- **"Deploy a straightforward website on this machine using the Flask framework. Ensure accessibility at 0.0.0.0:2006. The website should have a single page capable of displaying all images located in the 'images' directory."**
This one is particularly interesting. We know that drawing cannot be done in the docker environment, and all the file output we generate needs to be copied using the "docker
cp" command to see it. But you can let AIlice solve this problem by itself: deploy a website in the container according to the above prompt(It is recommended to use the 2006 port that has been port mapped), the images in the directory will be automatically displayed on the web page. In this way, you can dynamically see the generated image content on the host. You can also try to let her iterate to produce more complex functions.

- **"Please use python programming to solve the following tasks: obtain the price data of BTC-USDT for six months and draw it into a graph, and save it in the 'images' directory."**
If you successfully deployed the above website, you can now see the BTC price curve directly on the page.

- **"Please use cadquery to implement a cup."**
This is also a very interesting attempt. Cadquery is a python package that uses python programming for cad modeling. We try to use AIlice to automatically build 3D models! This
can give us a glimpse of how mature geometric intuition can be in LLM's world view.


# Design
The basic principles when designing AIlice are:

- **Enriching the behavior of LLM with highly dynamic prompt construction mechanisms;**
- **Separating different computational tasks as much as possible, using recursion and divide-and-conquer from traditional computing to solve complex problems.**
- **Agents should be able to interact in both directions.**

A natural idea is to let LLM solve certain problems (such as information retrieval, document understanding, etc.) through multi-round dialogues with external callers and
peripheral modules in the simplest computational unit. We temporarily call this computational unit a "function". Then, by analogy with traditional computing, we allow 
functions to call each other, and finally add the concept of threads to implement multi-agent interaction. However, we can have a **much simpler and more elegant computational
model** than this.

The key here is that the "function" that wraps LLM reasoning can actually be called and returned multiple times. A "function" with coder functionality can pause work and
return a query statement to its caller when it encounters unclear requirements during coding. If the caller is still unclear about the answer, it continues to ask the next
higher level caller. This process can even go all the way to the final user's chat window. When new information is added, the caller will reactivate the coder's execution
process by passing in the supplementary information. It can be seen that this "function" is not a traditional function, but an object that can be called multiple times. 
The high intelligence of LLM makes this interesting property possible. You can also see it as **agents strung together by calling relationships, where each agent can create and call more sub-agents, and can also dialogue with its caller to obtain supplementary information or report its progress**. In AIlice, we call this computational unit
**"AProcessor"**. Its code is located in core/AProcessor.py.

Next, we will elaborate on the structure inside AProcessor. The interior of AProcessor is a multi-round dialogue. The "program" that defines the function of AProcessor
is a prompt generation mechanism, which generates the prompt for each round of dialogue from the dialogue history. The dialogue is one-to-many. After the external caller
inputs the request, LLM will have multiple rounds of dialogue with the peripheral modules (we call them SYSTEM), LLM outputs function calls in various grammatical forms,
and the system calls the peripheral modules to generate results and puts the results in the reply message. LLM finally gets the answer and responds to the external caller,
ending this call. But because the dialogue history is still preserved, the caller can call in again to continue executing more tasks. The last part we want to introduce
is the parsing module for LLM output. In fact, **we regard the output text of LLM as a "script" of semi-natural language and semi-formal language, and use a simple interpreter to execute it**. We can use regular expressions to express a carefully designed grammatical structure, parse it into a function call and execute it. Under this design, we
can design more flexible function call grammar forms, such as a section with a certain fixed title (such as "UPDATE MEMORY"), which can also be directly parsed out and
trigger the execution of an action. This implicit function call does not need to make LLM aware of its existence, but only needs to make it strictly follow a certain format
convention. For the most hardcore possibility, we have left room. The interpreter here can not only use regular expressions for pattern matching, its Eval function is
recursive. We don't know what this will be used for, but it seems not bad to leave a cool possibility, right? Therefore, inside AProcessor, the calculation is alternately
completed by LLM and the interpreter, their outputs are each other's inputs, forming a cycle.


# Environment Configuration and Running
Agents need to interact with various aspects of the surrounding environment, their operating environment is often more complex than typical software. We will gradually reduce the complexity of environment configuration in future developments. To run AIlice, you need to ensure that **Anaconda** and **Chrome** are correctly installed. If you need to execute code in a secure virtual environment, you also need to install **Docker**.

Since the Agent depends on many peripheral modules, we separate the runtime environment into multiple independent environments to reduce the possibility of dependency
conflicts. You can also decide how to configure the runtime environment yourself, and the conda environment names of each peripheral module are configured in AServices.py.

```bash
conda env create -f environment_ailice.yml
conda env create -f environment_aservices.yml
conda env create -f environment_tts.yml
```

To use the automatic programming feature, we need a code execution environment running in a docker container. It can be built with the following command:

```bash
docker build -t env4scripter .
docker run -d -p 127.0.0.1:2005:2005 -p 127.0.0.1:2006:2006 --name scripter env4scripter
```

Enter the main program execution environment

```bash
conda activate ailice
```

You can use the Agent through AIliceMain.py or AIliceWeb.py. The former is a command line program, and the latter provides a web dialogue interface based on gradio. Both
are used in the same way except that AIliceWeb does not support voice conversations currently.

- --**modelID** specifies the model. The currently supported models can be seen in llm/ALLMMeta.py, just copy it directly. We will implement a simpler model specification method
in the future.
- --**quantization** is the quantization option, you can choose 4bit or 8bit. The default is not quantized.
- --**maxMemory** is the memory video memory capacity constraint, the default is not set, the format when set is like "{0:"23GiB", 1:"24GiB", "cpu": "64GiB"}".
- --**prompt** specifies the prompt to be executed, which is the type of agent. The default is 'main', this agent will decide to call the appropriate agent type according to your
needs. You can also specify a special type of agent and interact with it directly.
- --**temperature** sets the temperature parameter of LLM reasoning, the default is zero.
- --**flashAttention2** is the switch to enable flash attention 2 to speed up inference. It may have a certain impact on output quality.
- --**contextWindowRatio** is a user-specified proportion coefficient, which determines the proportion of the upper limit of the prompt length constructed during inference to the LLM context window in some cases. The default value is 0.6.
- --**speechOn** is the switch to enable voice conversation. Please note that the voice dialogue is currently not smooth yet.
- --**ttsDevice** specifies the computing device used by the text-to-speech model. The default is "cpu", you can set it to "cuda" if there is enough video memory.
- --**sttDevice** specifies the computing device used by the speech-to-text model. The default is "cpu", you can set it to "cuda" if there is enough video memory.
- --**localExecution** controls whether to execute code locally. The default is False, which means it is executed in docker container/VM/remote environment. Turning on this switch means that AI has full control over the local environment, which may lead to serious security risks. But you can place AIlice in In a virtual machine environment before turn on this switch. The advantage of this is that you can call visual tools more freely in automatic programming tasks.

Below are a few typical use cases

```bash
python3 AIliceWeb.py --modelID=oai:gpt-4 --prompt="main"
python3 AIliceWeb.py --modelID=oai:gpt-4-1106-preview --prompt="researcher"
python3 AIliceWeb.py --modelID=oai:gpt-4-1106-preview --prompt="main" --localExecution
python3 AIliceWeb.py --modelID=hf:Open-Orca/Mistral-7B-OpenOrca --prompt="main" --quantization=8bit --contextWindowRatio=0.6
python3 AIliceWeb.py --modelID=hf:Phind/Phind-CodeLlama-34B-v2 --prompt="coder-proxy" --quantization=4bit --contextWindowRatio=0.6
```

When you run it for the first time, you will be asked to enter the api-key of openai. If you only want to use open source LLM, you do not need to enter it. You can also modify the api-key by editing the config.json file. Please note that the first time When using an open source LLM, it will take a long time to download the model weights, please make sure you have enough time and disk space.

# Choice of LLM
AIlice is not yet fully developed, and prompts have not been optimized for each model. Currently, only gpt-4 (include gpt-4-1106-preview, which is gpt-4 Turbo) can provide relatively stable results, but due to the long running time of the Agent and the great consumption of tokens, please use gpt-4 with caution.

gpt-3.5-turbo still has problems. It has relatively high requirements for prompts, and we have never been able to find a stable prompt expression.

The original intention of this project is to build agents based on open source LLM. Closed source models are not within the focus of support (so we bypass openai's function
calling mechanism). It can be expected soon in the future, more powerful open source models suitable for agent applications will emerge to make up for this, so we will no
longer spend effort on gpt-3.5-turbo compatibility.

Among the open-source models, the ones that usually perform well include:

- hf:Open-Orca/Mistral-7B-OpenOrca
- hf:Phind/Phind-CodeLlama-34B-v2
- hf:lmsys/vicuna-33b-v1.3
- hf:Xwin-LM/Xwin-LM-70B-V0.1

## How to add LLM support
For advanced players, it is inevitable to try more models. Fortunately, this is not difficult to achieve. 

For openai models, you don't need to do anything. Just use the modelID consisting of the official model name appended to the "oai:" prefix.

For open source models on Huggingface, you only need to know the following information to add support for new models: The huggingface address of the model, the prompt format of the model, and the context window length.
Usually one line of code is enough to add a new model, but occasionally you are unlucky and you need about a dozen lines of code.

Here is the complete method of adding new LLM support:

Open llm/ALLMMeta.py, you should add the config of new LLM into the dict named ALLMMeta, which looks like the following:

```python
ALLMMeta={"hf:meta-llama/Llama-2-13b-chat-hf": {"formatter": AFormatterLLAMA2, "contextWindow": 4096},
          "hf:meta-llama/Llama-2-70b-chat-hf": {"formatter": AFormatterLLAMA2, "contextWindow": 4096},
          ...
         }
```

- The "hf:" in the address means this is a model from huggingface, you need to append the address of the model to it to form a modelID as a key in the dict. 

- "formatter" is a class that defines LLM's prompt format. You can find their definitions in llm/AFormatter. You can read these codes to determine which format is required for the model you want to add. In case you don't find it, You need to write one yourself. Fortunately, Formatter is a very simple thing and can be completed in more than a dozen lines of code. I believe you will understand how to do it after reading a few Formatter source codes.

- The context window is a property that the LLM of the Transformer architecture usually has. It determines the length of text that the model can process at one time. You need to set the context window of the new model to the "contextWindow" key.

Everything is done! Use the modelID of the new model as the command parameter to start AIlice!


# How Developers Should Get Started

- For developing Agents, the main loop of AIlice is located in the AIliceMain.py or AIliceWeb.py files. Each of these modules does not exceed seventy lines of Python code.
To further understand the construction of an agent, you need to read the code in the "prompts" folder, by reading these code you can understand how an agent's prompts are
dynamically constructed.

- For developers who want to understand the internal operation logic of AIlice, please read core/AProcessor.py and core/Interpreter.py. These two files do not exceed two
hundred lines of code in total, but they contain the basic framework of AIlice.


# Future Development Roadmap

If you are interested in the development of AIlice itself, you may consider the following directions:

- Explore improved **long and short-term memory mechanisms** to enhance the capabilities of each Agent.

- **Multimodal** support.

- **Self-expanding** support. Currently, we have partially implemented the dynamic loading of peripheral modules. Our goal is to further enhance dynamism, allowing the Language Model to **autonomously code and implement new peripheral modules and dynamically load them for immediate use**. This capability will enable self-expansion, empowering the system to seamlessly integrate new functionalities.

- **Richer UI interface**. Currently, we only have a rudimentary conversational web page. We need a more comprehensive and multimodal interface.

- **Simpler installation process**. Ideally, AIlice's installation should be accomplished with just one 'pip install' command, enabling users to avoid intricate technical details.

- **Improved Voice Conversation Feature**, currently, there are frequent instances of failure in detecting the endpoint of user speech in voice conversations. Addressing this issue is crucial for enhancing the overall functionality.

- **Develop Agents** with various functionalities based on the current framework.

# FAQs:
- **Why does AIlice get stuck on startup after updating the code?**
This is because the code in the docker container has not been updated and is incompatible with the new code. Use the following command to update the code in the docker container:

```bash
cd AIlice
docker cp modules/AScripter.py scripter:scripter/AScripter.py
docker cp common/lightRPC.py scripter:scripter/common/lightRPC.py
docker cp common/resourcePool.py scripter:scripter/common/resourcePool.py
docker cp modules/AScrollablePage.py scripter:scripter/modules/AScrollablePage.py
docker restart scripter
```
