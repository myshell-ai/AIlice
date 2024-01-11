
![AIlice](./AIlice.png)

# Why create another agent?
This is due to two reasons. 

First, we need **a simple framework that is easy to understand and sufficiently controllable** to test various new ideas about agents. This requires building a fully functional agent framework within a few thousand lines of code.

Second, despite the current strength of OpenAI's products, we place hope in the open-source community for the future. This is not only because of the idealistic desire to break the monopoly on AGI but also for technical reasons. We anticipate that **future agents will run for extended periods on local machines, performing various complex tasks from local data analysis to information investigations on the internet**. Many of these tasks require good reasoning abilities rather than vast amounts of knowledge. We hope that in the future, a lightweight, high-reasoning-capacity open-source LLM will emerge to realize this ideal.

# Comparison

We have designed several dimensions to compare AIlice with mainstream AI agents. These include:

- **Multi-agents**:
Whether problems are addressed through multi-agent dialogues. This can enhance fault tolerance.

- **Dynamic Creation**:
The ability to dynamically create agents during task execution. This helps to break down tasks into subtasks, reducing context consumption within agents.

- **Interactive Calling**:
Whether dynamically created agents can interact with their creators (callers). This improves fault tolerance for subtask failures and allows users to naturally participate as collaborators.

- **Long Term Memory**:
The technical solutions used for long-term memory. Enabling LLM to surpass its context window constraints and accomplish more complex tasks.

- **Function Call Syntax**:
The syntax for function calls. Diverse syntax supports provide LLM with more flexible ways of external interaction.

- **Self-expansion**:
Modules for self-expansion. Allowing the agent to build more functionalities for itself, avoiding the manual development of numerous external interaction modules.

- **Multimodal**:
Support for multimodal models. The support for multimodal models will enable the agent to have a broader range of applications.

- **Code Size**:
The number of lines of code. A smaller codebase enables developers to better understand its internal logic and exert stronger control over the code. Ultimately, simple code implementation makes self-reflection and self-expansion for the agent simpler.

Please note that this is an ongoing research, and the data in the table may be inaccurate due to oversights in my investigation or rapid progress in these projects. If any errors are identified, please point them out.

|  | Multi-agents | Dynamic Creation | Interactive Calling | Long Term Memory | Function Call Syntax | Self-expansion | Multimodal | Code Size |
|:------:|:------:|:------:|:------:|:------:|:------:|:------:|:------:|:------:|
| AutoGen | Y | Y | N | RAG and more | JSON | N | Y | 20851 |
| AIlice | Y | Y | Y | RAG and more, in dev | Arbitrary | Y | in dev | 2772 |

The number of lines of code is calculated in the latest code base via the "git ls-files "*.py" | xargs wc -l" command.


# Introduction

AIlice is a lightweight AI Agent under development, which also serves as a simple development framework for quickly building and experimenting with various AI Agent ideas.
Her features are briefly listed as follows:

- **Natural and highly fault-tolerant Interactive Agents Calling Tree architecture.**
- **Parsing LLM output in the most flexible way possible, supporting more varied function call mechanisms.**
- **Self-constructing and dynamically loading environment interaction modules, offering limitless potential for feature expansion.**
- **Designed for open-source models but seamlessly supports commercial models like GPT-4.**
- **Supports in-depth investigations on specific topics.**
- **Automation programming and script execution. It serves as an all-encompassing coder and a proficient system management tool, mastering all system commands—akin to an AI operating system.**


# COOL things we can do
Let's list some typical use cases. I frequently employ these examples to test AIlice during development, ensuring stable performance. However, even with these tests, the execution results are influenced by the chosen model, code version, and even the testing time. (GPT-4 may experience a decrease in performance under high loads, while open-source models, of course, don't have this issue; they don't have much room for degradation) Additionally, AIlice is an agent based on multi-agent cooperation, and as a user, you are also one of the "agents". Hence, when AIlice requires additional information, it will seek input from you, and the thoroughness of your details is crucial for her success. Furthermore, if the task execution falls short, you can guide her in the right direction, and she will rectify her approach.

The last point to note is that AIlice currently lacks a runtime control mechanism, so she might get stuck in a loop or run for an extended period. When using a commercial LLM runtime, you need to monitor her operation closely.

- **"Please list the contents of the current directory."**

- **"Find David Tong's QFT lecture notes and download them to the "physics" folder in the current directory. You may need to create the folder first."**

- **"Deploy a straightforward website on this machine using the Flask framework. Ensure accessibility at 0.0.0.0:59001. The website should have a single page capable of displaying all images located in the 'images' directory."**
This one is particularly interesting. We know that drawing cannot be done in the docker environment, and all the file output we generate needs to be copied using the "docker
cp" command to see it. But you can let AIlice solve this problem by itself: deploy a website in the container according to the above prompt(It is recommended to use ports between 59001 and 59200 that has been port mapped), the images in the directory will be automatically displayed on the web page. In this way, you can dynamically see the generated image content on the host. You can also try to let her iterate to produce more complex functions. If you don't see any images on the page, please check whether the "images" folder of the website is different from the "images" folder here (for example, it might be under "static/images").

- **"Please use python programming to solve the following tasks: obtain the price data of BTC-USDT for six months and draw it into a graph, and save it in the 'images' directory."**
If you successfully deployed the above website, you can now see the BTC price curve directly on the page.


- **"Find the process on port 59001 and terminate it."**
This will terminate the website service program that was just established.

- **"Please use cadquery to implement a cup."**
This is also a very interesting attempt. Cadquery is a python package that uses python programming for cad modeling. We try to use AIlice to automatically build 3D models! This
can give us a glimpse of how mature geometric intuition can be in LLM's world view. Of course, after implementing multimodal support, we can enable AIlice to see the models she creates, allowing for further adjustments and establishing a highly effective feedback loop. This way, it might be possible to achieve truly usable language-controlled 3D modeling.

- **"Please search the internet for 100 tutorials in various branches of physics and download the PDF files you find to a folder named 'physics'. There is no need to verify the content of pdfs, we only need a rough collection for now."** Utilizing AIlice to achieve automatic data set collection and construction is one of our ongoing objectives. Currently, the researcher employed for this functionality still has some deficiencies, but it is already capable of providing some intriguing results.

- **"Please conduct an investigation on open-source PDF OCR tools, with a focus on those capable of recognizing mathematical formulas and converting them into LaTeX code. Consolidate the findings into a report."**

- **"Please write an ext-module. The function of the module is to obtain the content of related pages on the wiki through keywords."** AIlice can construct external interaction modules (we call it ext-modules) on her own, thereby endowing her with unlimited extensibility. All it takes is a few prompts from you. Once the module is constructed, you can instruct AIlice by saying, "Please load the newly implemented wiki module and utilize it to query the entry on relativity."


# Design
The basic principles when designing AIlice are:

- **Enriching the behavior of LLM with highly dynamic prompt construction mechanisms;**
- **Separating different computational tasks as much as possible, using recursion and divide-and-conquer from traditional computing to solve complex problems.**
- **Agents should be able to interact in both directions.**

Let's briefly explain these fundamental principles.

Starting from the most obvious level, a highly dynamic prompt construction makes it less likely for an agent to fall into a loop. The influx of new variables from the external environment continuously impacts the LLM, helping it to avoid that pitfall. Furthermore, feeding the LLM with all the currently available information can greatly improve its output. For example, in automated programming, error messages from interpreters or command lines assist the LLM in continuously modifying the code until the correct result is achieved. Lastly, in dynamic prompt construction, new information in the prompts may also come from other agents, which acts as a form of linked inference computation, making the system's computational mechanisms more complex, varied, and capable of producing richer behaviors.

Separating computational tasks is, from a practical standpoint, due to our limited context window. We cannot expect to complete a complex task within a window of a few thousand tokens. If we can decompose a complex task so that each subtask is solved within limited resources, that would be an ideal outcome. In traditional computing models, we have always taken advantage of this, but in new computing centered around LLMs, this is not easy to achieve. The issue is that if one subtask fails, the entire task is at risk of failure. Recursion is even more challenging: how do you ensure that with each call, the LLM solves a part of the subproblem rather than passing the entire burden to the next level of the call? We have solved the first problem with the IACT architecture in AIlice, and the second problem is theoretically not difficult to solve, but it likely requires a smarter LLM.

The third principle is what everyone is currently working on: having multiple intelligent agents interact and cooperate to complete more complex tasks. The implementation of this principle actually addresses the aforementioned issue of subtask failure. Multi-agent collaboration is crucial for the fault tolerance of agents in operation. In fact, this may be one of the biggest differences between the new computational paradigm and traditional computing: traditional computing is precise and error-free, assigning subtasks only through unidirectional communication (function calls), whereas the new computational paradigm is error-prone and requires bidirectional communication between computing units to correct errors. This will be explained in detail in the following section on the IACT framework.


## Computational Model: Interactive Agents Calling Tree
![IACT](./IACT.jpg)
*IACT Architecture Diagram. A user requirement to build a page for image collection and display is dynamically decomposed into two tasks: coder_spider and coder_website. When coder_spider encounters difficulties, it proactively seeks assistance from its caller, proxy_cat_gallery. Proxy_cat_gallery then creates another agent, researcher_api, and employs it to address the issue.*

AIlice can be regarded as **a computer powered by a LLM**, and its features include:

- Representing input, output, programs, and data in text form.

- Using LLM as the processor.

- Breaking down computational tasks through successive calls to basic computing units (analogous to functions in traditional computing), which are essentially various functional agents.

Therefore, **user-input text commands are executed as a kind of program, decomposed into various "subprograms", and addressed by different agents**, forming the fundamental architecture of AIlice. In the following, we will provide a detailed explanation of the nature of these basic computing units.

A natural idea is to let LLM solve certain problems (such as information retrieval, document understanding, etc.) through multi-round dialogues with external callers and
peripheral modules in the simplest computational unit. We temporarily call this computational unit a "function". Then, by analogy with traditional computing, we allow 
functions to call each other, and finally add the concept of threads to implement multi-agent interaction. However, we can have a **much simpler and more elegant computational
model** than this.

The key here is that the "function" that wraps LLM reasoning can actually be called and returned multiple times. A "function" with coder functionality can pause work and
return a query statement to its caller when it encounters unclear requirements during coding. If the caller is still unclear about the answer, it continues to ask the next
higher level caller. This process can even go all the way to the final user's chat window. When new information is added, the caller will reactivate the coder's execution
process by passing in the supplementary information. It can be seen that this "function" is not a traditional function, but an object that can be called multiple times. 
The high intelligence of LLM makes this interesting property possible. You can also see it as **agents strung together by calling relationships, where each agent can create and call more sub-agents, and can also dialogue with its caller to obtain supplementary information or report its progress**. In AIlice, we call this computational unit
**"AProcessor"**(essentially what we referred to as an agent). Its code is located in core/AProcessor.py.

## Basic Computing Unit: Tai Chi Diagram of LLM and Interpreter
Next, we will elaborate on the structure inside AProcessor. The interior of AProcessor is a multi-round dialogue. The "program" that defines the function of AProcessor
is a prompt generation mechanism, which generates the prompt for each round of dialogue from the dialogue history. The dialogue is one-to-many. After the external caller
inputs the request, LLM will have multiple rounds of dialogue with the peripheral modules (we call them SYSTEM), LLM outputs function calls in various grammatical forms,
and the system calls the peripheral modules to generate results and puts the results in the reply message. LLM finally gets the answer and responds to the external caller,
ending this call. But because the dialogue history is still preserved, the caller can call in again to continue executing more tasks. 

The last part we want to introduce
is the parsing module for LLM output. In fact, **we regard the output text of LLM as a "script" of semi-natural language and semi-formal language, and use a simple interpreter to execute it**. We can use regular expressions to express a carefully designed grammatical structure, parse it into a function call and execute it. Under this design, we
can design more flexible function call grammar forms, such as a section with a certain fixed title (such as "UPDATE MEMORY"), which can also be directly parsed out and
trigger the execution of an action. This implicit function call does not need to make LLM aware of its existence, but only needs to make it strictly follow a certain format
convention. For the most hardcore possibility, we have left room. The interpreter here can not only use regular expressions for pattern matching, its Eval function is
recursive. We don't know what this will be used for, but it seems not bad to leave a cool possibility, right? Therefore, inside AProcessor, the calculation is alternately
completed by LLM and the interpreter, their outputs are each other's inputs, forming a cycle.


# Environment Configuration and Running
Agents need to interact with various aspects of the surrounding environment, their operating environment is often more complex than typical software. It may take us a long time to install the dependencies, but fortunately, this is basically done automatically.

To run AIlice, you need to ensure that **Chrome** are correctly installed. If you need to execute code in a secure virtual environment, you also need to install **Docker**.

You can use the following command to install AIlice (It is strongly recommended to use tools such as conda to create a new virtual environment to install AIlice, so as to avoid dependency conflicts):

```bash
git clone https://github.com/myshell-ai/AIlice.git
cd AIlice
pip install -e .
```

For users who need to use the voice dialogue or model fine-tuning function, you can use one of the following command:

```bash
pip install -e .[speech]
pip install -e .[finetuning]
```

To use the automatic programming feature, we need a code execution environment running in a docker container. It can be built with the following command:

```bash
docker build -t env4scripter .
docker run -d -p 127.0.0.1:59000-59200:59000-59200 --name scripter env4scripter
```

Now that the environment configuration has been done, you can directly copy a command from the typical use cases below to run AIlice.

```bash
ailice_main --modelID=oai:gpt-4-1106-preview --prompt="main"
ailice_main --modelID=oai:gpt-4-1106-preview --prompt="researcher" --trace=./trace
ailice_main --modelID=oai:gpt-4-1106-preview --prompt="main" --localExecution
ailice_main --modelID=hf:Open-Orca/Mistral-7B-OpenOrca --prompt="main" --quantization=8bit --contextWindowRatio=0.6
ailice_web --modelID=hf:openchat/openchat_3.5 --prompt="main" --quantization=8bit --contextWindowRatio=0.6
ailice_web --modelID=hf:ehartford/dolphin-2.5-mixtral-8x7b --prompt="main" --quantization=4bit --contextWindowRatio=0.3
ailice_web --modelID=hf:Phind/Phind-CodeLlama-34B-v2 --prompt="coder-proxy" --quantization=4bit --contextWindowRatio=0.6
```

When you run it for the first time, you will be asked to enter the api-key of openai. If you only want to use open source LLM, you do not need to enter it. You can also modify the api-key by editing the config.json file. Please note that the first time When using an open source LLM, it will take a long time to download the model weights, please make sure you have enough time and disk space.

As shown in the examples, you can use the Agent through AIliceMain.py or AIliceWeb.py. The former is a command line program, and the latter provides a web dialogue interface based on gradio. Both are used in the same way except that AIliceWeb does not support voice conversations currently.

- --**modelID** specifies the model. The currently supported models can be seen in core/llm/ALLMMeta.py, just copy it directly. We will implement a simpler model specification method
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
- --**trace** is used to specify the output directory for the execution history data. This option is empty by default, indicating that the execution history recording feature is not enabled.

AIlice may get stuck after the code is updated. This is because the code in the docker container has not been updated. Please execute the following command to update the docker container.

```bash
cd AIlice
docker cp ailice/__init__.py scripter:scripter/ailice/__init__.py
docker cp ailice/common/__init__.py scripter:scripter/ailice/common/__init__.py
docker cp ailice/common/lightRPC.py scripter:scripter/ailice/common/lightRPC.py
docker cp ailice/modules/__init__.py scripter:scripter/ailice/modules/__init__.py
docker cp ailice/modules/AScripter.py scripter:scripter/ailice/modules/AScripter.py
docker cp ailice/modules/AScrollablePage.py scripter:scripter/ailice/modules/AScrollablePage.py
docker restart scripter
```

# Choice of LLM
AIlice is not yet fully developed, and prompts have not been optimized for each model. Currently, only gpt-4 (include gpt-4-1106-preview, which is gpt-4 Turbo) can provide relatively stable results, but due to the long running time of the Agent and the great consumption of tokens, please use gpt-4 with caution.

gpt-3.5-turbo still has problems. It has relatively high requirements for prompts, and we have never been able to find a stable prompt expression.

The original intention of this project is to build agents based on open source LLM. Closed source models are not within the focus of support (so we bypass openai's function
calling mechanism). It can be expected soon in the future, more powerful open source models suitable for agent applications will emerge to make up for this, so we will no
longer spend effort on gpt-3.5-turbo compatibility.

Among the open-source models, the ones that usually perform well include:

- hf:Open-Orca/Mistral-7B-OpenOrca
- hf:openchat/openchat_3.5
- hf:ehartford/dolphin-2.5-mixtral-8x7b
- hf:Phind/Phind-CodeLlama-34B-v2

## How to add LLM support
For advanced players, it is inevitable to try more models. Fortunately, this is not difficult to achieve. 

For openai models, you don't need to do anything. Just use the modelID consisting of the official model name appended to the "oai:" prefix.

For open source models on Huggingface, you only need to know the following information to add support for new models: The huggingface address of the model, the prompt format of the model, and the context window length.
Usually one line of code is enough to add a new model, but occasionally you are unlucky and you need about a dozen lines of code.

Here is the complete method of adding new LLM support:

Open core/llm/ALLMMeta.py, you should add the config of new LLM into the dict named ALLMMeta, which looks like the following:

```python
ALLMMeta={"hf:meta-llama/Llama-2-13b-chat-hf": {"formatter": AFormatterLLAMA2, "contextWindow": 4096, "systemAsUser": False},
          "hf:meta-llama/Llama-2-70b-chat-hf": {"formatter": AFormatterLLAMA2, "contextWindow": 4096, "systemAsUser": False},
          ...
         }
```

- The "hf:" in the address means this is a model from huggingface, you need to append the address of the model to it to form a modelID as a key in the dict. 

- "formatter" is a class that defines LLM's prompt format. You can find their definitions in core/llm/AFormatter. You can read these codes to determine which format is required for the model you want to add. In case you don't find it, You need to write one yourself. Fortunately, Formatter is a very simple thing and can be completed in more than a dozen lines of code. I believe you will understand how to do it after reading a few Formatter source codes.

- The context window is a property that the LLM of the Transformer architecture usually has. It determines the length of text that the model can process at one time. You need to set the context window of the new model to the "contextWindow" key.

- "systemAsUser": We use the "system" role as the sender of the message returned by the function calls. However, not all LLMs have a clear definition of system role, and there is no guarantee that the LLM can adapt to this approach. So we need to use systemAsUser to set whether to put the text returned by the function calls in user messages. Try to set it to False first.

Everything is done! Use the modelID of the new model as the command parameter to start AIlice!


# How Developers Should Get Started

- For developing Agents, the main loop of AIlice is located in the AIliceMain.py or AIliceWeb.py files. Each of these modules does not exceed seventy lines of Python code.
To further understand the construction of an agent, you need to read the code in the "prompts" folder, by reading these code you can understand how an agent's prompts are
dynamically constructed.

- For developers who want to understand the internal operation logic of AIlice, please read core/AProcessor.py and core/Interpreter.py. These two files do not exceed two
hundred lines of code in total, but they contain the basic framework of AIlice.


# Future Development Roadmap

AIlice's fundamental tasks are twofold: **one is to fully unleash the capabilities of LLM based on text into the real world; the other is to explore better mechanisms for long-term memory and forming a coherent understanding of vast amounts of text**. Our development efforts revolve around these two focal points.

If you are interested in the development of AIlice itself, you may consider the following directions:

- Explore improved **long-term memory mechanisms** to enhance the capabilities of each Agent.

- **Multimodal** support.

- **Self-expanding** support. Our goal is to enable language models to **autonomously code and implement new peripheral modules and dynamically load them for immediate use**. This capability will enable self-expansion, empowering the system to seamlessly integrate new functionalities. It has been implemented, but it still needs to be improved so that various agents can easily use dynamically loaded modules.

- **Introducing more script language features beyond function calls, unleashing LLM's text manipulation capabilities.** For example, one of the most pressing needs is for LLM to have the ability to define and reference text variables. This grants it a named-access storage mechanism, expanding the context window, while also allowing it to avoid unnecessary copying when transmitting large code segments.

- **Richer UI interface**. Currently, we only have a rudimentary conversational web page. We need a more comprehensive and multimodal interface.

- **Improved Voice Conversation Feature**, currently, there are frequent instances of failure in detecting the endpoint of user speech in voice conversations. Addressing this issue is crucial for enhancing the overall functionality.

- **Considering using a simple implementation of a vector database as a replacement for ChromaDB.** it introduces too many additional dependencies.

- **Develop Agents** with various functionalities based on the current framework.

In addition to the tasks mentioned above, we should also start actively contemplating the possibility of **creating a smaller LLM that possesses lower knowledge content but higher reasoning abilities**.
