import torch
import os
import json
from PIL import Image
from datasets import load_dataset
from transformers import LlavaNextForConditionalGeneration, AutoProcessor, BitsAndBytesConfig, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model

os.environ["PYTHONUTF8"] = "1"

model_path = "./model"
dataset_path = "dataset/train.jsonl"
image_base_dir = "dataset/images"

quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4"
)

model = LlavaNextForConditionalGeneration.from_pretrained(
    model_path,
    quantization_config=quantization_config,
    device_map="auto"
)
processor = AutoProcessor.from_pretrained(model_path)
peft_config = LoraConfig(
    r=16, 
    lora_alpha=32, 
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"], 
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, peft_config)

model.print_trainable_parameters()

def format_data(example):
    text = ""
    for msg in example['conversations']:
        if msg['from'] == 'human':
            
            content = msg['value'].replace('<image>', '').strip()
            text += f"USER: <image>\n{content}\n"
        elif msg['from'] == 'gpt':
            text += f"ASSISTANT: {msg['value']}</s>"
    
    return {"text": text, "image": example['image']}

raw_dataset = load_dataset("json", data_files=dataset_path, split="train")
#dataset = raw_dataset.map(format_data)
dataset = raw_dataset.select(range(3)).map(format_data)

def collator(features):
    images = []
    texts = []
    for f in features:
        image_path = os.path.join(image_base_dir, os.path.basename(f['image']))
        images.append(Image.open(image_path).convert("RGB"))
        texts.append(f['text'])
    
  
    batch = processor(text=texts, images=images, return_tensors="pt", padding=True, truncation=True)
    batch["labels"] = batch["input_ids"].clone()
    
    batch["labels"][batch["input_ids"] == processor.tokenizer.pad_token_id] = -100
    return batch



training_args = TrainingArguments(
    output_dir="./llava-finetuned",
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,
    gradient_checkpointing=True,
    learning_rate=2e-4,
    num_train_epochs=3,
    save_strategy="epoch",
    fp16=True,
    remove_unused_columns=False
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset,
    data_collator=collator
)

trainer.train()