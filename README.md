# Introduction
AIlice is a lightweight AI Agent under development, which also serves as a simple development framework for quickly building and experimenting with various AI Agent ideas.
Her features are briefly listed as follows:

- Natural multi-Agent invocation and interaction mechanism.
- Parsing LLM output in the most flexible way possible, supporting more varied function call mechanisms.
- Support for various open-source LLMs and commercial models like gpt-4.
- Support for peripheral modules such as web page, pdf browsing, searching, sh, Python code execution, voice dialogue, etc. which run as RPC services in a separable runtime 
environment.

# Design
The basic principles when designing AIlice are:

- Enriching the behavior of LLM with highly dynamic prompt construction mechanisms;
- Separating different computational tasks as much as possible, using recursion and divide-and-conquer from traditional computing to solve complex problems.
- Agents should be able to interact. 

A natural idea is to let LLM solve certain problems (such as information retrieval, document understanding, etc.) through multi-round dialogues with external callers and
peripheral modules in the simplest computational unit. We temporarily call this computational unit a "function". Then, by analogy with traditional computing, we allow 
functions to call each other, and finally add the concept of threads to implement multi-agent interaction. However, we can have a much simpler and more elegant computational
model than this.

The key here is that the "function" that wraps LLM reasoning can actually be called and returned multiple times. A "function" with coder functionality can pause work and
return a query statement to its caller when it encounters unclear requirements during coding. If the caller is still unclear about the answer, it continues to ask the next
higher level caller. This process can even go all the way to the final user's chat window. When new information is added, the caller will reactivate the coder's execution
process by passing in the supplementary information. It can be seen that this "function" is not a traditional function, but an object that can be called multiple times. 
The high intelligence of LLM makes this interesting property possible. You can also see it as agents strung together by calling relationships, where each agent can create
and call more sub-agents, and can also dialogue with its caller to obtain supplementary information or report its progress. In AIlice, we call this computational unit
"AProcessor". Its code is located in core/AProcessor.py.

Next, we will elaborate on the structure inside AProcessor. The interior of AProcessor is a multi-round dialogue. The "program" that defines the function of AProcessor
is a prompt generation mechanism, which generates the prompt for each round of dialogue from the dialogue history. The dialogue is one-to-many. After the external caller
inputs the request, LLM will have multiple rounds of dialogue with the peripheral modules (we call them SYSTEM), LLM outputs function calls in various grammatical forms,
and the system calls the peripheral modules to generate results and puts the results in the reply message. LLM finally gets the answer and responds to the external caller,
ending this call. But because the dialogue history is still preserved, the caller can call in again to continue executing more tasks. The last part we want to introduce
is the parsing module for LLM output. In fact, we regard the output text of LLM as a "script" of semi-natural language and semi-formal language, and use a simple interpreter
to execute it. We can use regular expressions to express a carefully designed grammatical structure, parse it into a function call and execute it. Under this design, we
can design more flexible function call grammar forms, such as a section with a certain fixed title (such as "UPDATE MEMORY"), which can also be directly parsed out and
trigger the execution of an action. This implicit function call does not need to make LLM aware of its existence, but only needs to make it strictly follow a certain format
convention. For the most hardcore possibility, we have left room. The interpreter here can not only use regular expressions for pattern matching, its Eval function is
recursive. We don't know what this will be used for, but it seems not bad to leave a cool possibility, right? Therefore, inside AProcessor, the calculation is alternately
completed by LLM and the interpreter, their outputs are each other's inputs, forming a cycle.

# Environment Configuration and Running
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
docker run -d -p 127.0.0.1:2005:2005 -p 127.0.0.1:443:443 --name scripter env4scripter
```

Enter the main program execution environment

```bash
conda activate ailice
```

You can use the Agent through AIliceMain.py or AIliceWeb.py. The former is a command line program, and the latter provides a web dialogue interface based on gradio. Both
are used in the same way.
--modelID specifies the model. The currently supported models can be seen in llm/ALLMPool.py, just copy it directly. We will implement a simpler model specification method
in the future.
--quantization is the quantization option, you can choose 4bit or 8bit. The default is not quantized.
--maxMemory is the memory video memory capacity constraint, the default is not set, the format when set is like "{0:"23GiB", 1:"24GiB", "cpu": "64GiB"}".
--prompt specifies the prompt to be executed, which is the type of agent. The default is main, this agent will decide to call the appropriate agent type according to your
needs. You can also specify a special type of agent and interact with it directly.
--temperature sets the temperature parameter of LLM reasoning, the default is zero.

Below are a few typical use cases

```bash
python3 AIliceWeb.py --modelID=oai:gpt-4 --prompt="main"
python3 AIliceWeb.py --modelID=hf:Open-Orca/Mistral-7B-OpenOrca --prompt="main"
python3 AIliceWeb.py --modelID=hf:Phind/Phind-CodeLlama-34B-v2 --maxMemory={0:"23GiB", 1:"24GiB", "cpu": "64GiB"} --prompt="coder-proxy"
```

# Choice of LLM
AIlice is not yet fully developed, and prompts have not been optimized for each model. Currently, only gpt-4 can provide relatively stable results, but due to the long
running time of the Agent and the great consumption of tokens, please use gpt-4 with caution.
Gpt-3.5-turbo is not performing well due to some unknown prompt issues and needs to be improved.
Among the open-source models, the ones that usually perform well include:

- hf:Open-Orca/Mistral-7B-OpenOrca
- hf:Phind/Phind-CodeLlama-34B-v2
- hf:lmsys/vicuna-33b-v1.3
- hf:Xwin-LM/Xwin-LM-70B-V0.1

# How Developers Should Get Started

- For developing Agents, the best tutorials are undoubtedly the AIliceMain.py and AIliceWeb.py files. Each of these modules does not exceed seventy lines of Python code,
but they are enough to understand the basic elements of writing an Agent based on AIlice.

- For developers who want to understand the internal operation logic of AIlice, please read core/AProcessor.py and core/Interpreter.py. These two files do not exceed two
hundred lines of code in total, but they contain the basic framework of AIlice.


