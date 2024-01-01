from datasets import load_dataset
import os
import torch
import torch.nn.functional as F
import transformers

from peft import (
    LoraConfig,
    get_peft_model,
    get_peft_model_state_dict,
    prepare_model_for_kbit_training,
)

from ailice.core.llm.AFormatter import AFormatterChatML


BATCH_SIZE = 128
MICRO_BATCH_SIZE = 2
GRADIENT_ACCUMULATION_STEPS = BATCH_SIZE // MICRO_BATCH_SIZE
LEARNING_RATE = 3e-4
TRAIN_STEPS = 4
MAX_WINDOW = 8192

LORA_R = 64
LORA_ALPHA = 16
LORA_DROPOUT= 0.1
LORA_TARGET_MODULES = [
    "q_proj",
    "v_proj",
    "k_proj",
    "o_proj",
    "gate_proj"
]

class MyDataCollatorWithPadding(transformers.DataCollatorWithPadding):
    def __init__(self, tokenizer, padding=True, return_tensors="pt"):
        super().__init__(tokenizer, padding=padding, return_tensors=return_tensors)
        return

    def __call__(self, features):
        labels = [feature["labels"] for feature in features]
        maxLabelLength = max(len(label) for label in labels)
        paddedLabels = [F.pad(label, pad=(0, maxLabelLength - len(label)), value=self.tokenizer.pad_token_id) for label in labels]
        features = [{k: v for k, v in feature.items() if k != 'labels'} for feature in features]
        batch = super().__call__(features)
        batch["labels"] = torch.stack(paddedLabels)
        return batch

    
def finetune(modelLocation, dataset: str, dataDir: str, outDir: str, logDir: str):
    ds = load_dataset(dataset, data_dir=dataDir)

    tokenizer = transformers.AutoTokenizer.from_pretrained(modelLocation, truncation=True, max_length=MAX_WINDOW, add_special_tokens=True, add_bos_token=False, add_eos_token=False, legacy=False)
    tokenizer.pad_token = tokenizer.unk_token
    #tokenizer.add_special_tokens({'pad_token': '[PAD]'})
    quant_config = transformers.BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    model = transformers.AutoModelForCausalLM.from_pretrained(modelLocation,
                                                              quantization_config=quant_config,
                                                              device_map="auto"
                                                            )
    model = prepare_model_for_kbit_training(model)

    def tokenizeOpenorca(batch):
        concatenatedSamples = [
            f"<|im_start|>system\n{system_prompt}\n<|im_end|>\n<|im_start|>user\n{question}\n<|im_end|>\n<|im_start|>assistant\n{response}\n<|im_end|>"
            for system_prompt, question, response in zip(batch['system_prompt'], batch['question'], batch['response'])
        ]
        tokenizedInputs = tokenizer(
            concatenatedSamples,
            padding=True,
            truncation=True,
            max_length=MAX_WINDOW,
            return_tensors='pt'
        )
        return tokenizedInputs

    def tokenizeAIlice(batch):
        formatter = AFormatterChatML(tokenizer=None, systemAsUser=False)
        concatenatedSamples = [
            formatter(prompt0="",conversations=[{"role": role, "msg": msg} for role,msg in zip(conv['role'], conv['msg'])], encode=False, assistTag=False)
            for conv in batch['conversations']
        ]
        tokenizedInputs = tokenizer(
            concatenatedSamples,
            padding=True,
            truncation=True,
            max_length=MAX_WINDOW,
            return_tensors='pt'
        )
        return tokenizedInputs
    
    #trainData = ds['train'].select(list(range(100))).map(tokenizeOpenorca, batched=True, num_proc=32, remove_columns=["system_prompt","question","response","id"])
    trainData = ds['train'].map(tokenizeAIlice, batched=True, num_proc=32, remove_columns=["conversations"])
    trainData = trainData.add_column('labels',trainData["input_ids"])
    trainData = trainData.with_format("torch")
    
    config = LoraConfig(
    r=LORA_R,
    lora_alpha=LORA_ALPHA,
    target_modules=LORA_TARGET_MODULES,
    lora_dropout=LORA_DROPOUT,
    bias="none",
    task_type="CAUSAL_LM",
    #inference_mode=False
    )
    
    model = get_peft_model(model, config)
    model.print_trainable_parameters()
    
    trainingArguments = transformers.TrainingArguments(
        per_device_train_batch_size=MICRO_BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        warmup_ratio=0.1,
        #warmup_steps=100,
        num_train_epochs=1,
        #max_steps=TRAIN_STEPS,
        learning_rate=LEARNING_RATE,
        fp16=True,
        logging_steps=10,
        optim="adamw_torch",
        evaluation_strategy="no",
        save_strategy="steps",
        eval_steps=50,
        save_steps=50,
        output_dir=outDir,
        save_total_limit=3,
        load_best_model_at_end=False,
        report_to="tensorboard",
        logging_dir=logDir
        #remove_unused_columns=False
    )

    collator = MyDataCollatorWithPadding(tokenizer=tokenizer, return_tensors='pt', padding=True)

    trainer = transformers.Trainer(
        model=model,
        train_dataset=trainData,
        #eval_dataset=valid_data,
        args=trainingArguments,
        data_collator=collator
    )
    model.config.use_cache = False
    model = torch.compile(model)
    trainer.train()
    model.save_pretrained(outDir)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--model',type=str,default='openchat/openchat_3.5',help="")
    parser.add_argument('--dataset',type=str,default=f'{os.path.dirname(os.path.abspath(__file__))}/ADatasetTrace.py',help="")
    parser.add_argument('--datadir',type=str,default=None,help="")
    parser.add_argument('--outdir',type=str,default=None,required=True,help="")
    parser.add_argument('--logdir',type=str,default=None,help="")
    args = parser.parse_args()
    
    if ('ailice.finetuning.ADatasetTrace' == args.dataset) and (None == args.datadir):
        print("--datadir is required when using ADatasetTrace.")
        exit(0)
    
    finetune(modelLocation=args.model, dataset=args.dataset, dataDir=args.datadir, outDir=args.outdir, logDir=args.logdir)