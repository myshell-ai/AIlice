from llm.AFormatter import AFormatterSimple,AFormatterLLAMA2,AFormatterVicuna,AFormatterChatML,AFormatterAMAZON, AFormatterZephyr


ALLMMeta={"hf:meta-llama/Llama-2-13b-chat-hf": {"formatter": AFormatterLLAMA2, "contextWindow": 4096},
          "hf:meta-llama/Llama-2-70b-chat-hf": {"formatter": AFormatterLLAMA2, "contextWindow": 4096},
          "hf:upstage/llama-30b-instruct-2048": {"formatter": AFormatterSimple, "contextWindow": 2048},
          "hf:lmsys/vicuna-33b-v1.3": {"formatter": AFormatterVicuna, "contextWindow": 2048},
          "hf:Phind/Phind-CodeLlama-34B-v2": {"formatter": AFormatterSimple, "contextWindow": 4096},
          "hf:Xwin-LM/Xwin-LM-70B-V0.1": {"formatter": AFormatterVicuna, "contextWindow": 4096},
          "hf:Xwin-LM/Xwin-LM-13B-V0.1": {"formatter": AFormatterVicuna, "contextWindow": 4096},
          "hf:mistralai/Mistral-7B-Instruct-v0.1": {"formatter": AFormatterLLAMA2, "contextWindow": 8192},
          "hf:Open-Orca/Mistral-7B-OpenOrca": {"formatter": AFormatterChatML, "contextWindow": 8192},
          "hf:teknium/OpenHermes-2.5-Mistral-7B": {"formatter": AFormatterChatML, "contextWindow": 8192},
          "hf:Intel/neural-chat-7b-v3-1": {"formatter": AFormatterSimple, "contextWindow": 8192},
          "hf:amazon/MistralLite": {"formatter": AFormatterAMAZON, "contextWindow": 16384},
          "hf:HuggingFaceH4/zephyr-7b-beta": {"formatter": AFormatterZephyr, "contextWindow": 8192},
          "hf:THUDM/agentlm-13b": {"formatter": AFormatterLLAMA2, "contextWindow": 4096}}