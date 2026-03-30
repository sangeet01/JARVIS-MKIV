"""
JARVIS-MKIII Local LoRA Training Script
Requires NVIDIA GPU with 8GB+ VRAM.
"""
import os
import sys
import json
from pathlib import Path

DATASET_PATH = Path(__file__).parent / "dataset.jsonl"
OUTPUT_PATH = Path(__file__).parent / "jarvis_lora_adapter"
MIN_VRAM_GB = 8


def check_gpu():
    try:
        import torch
        if not torch.cuda.is_available():
            return None, 0
        vram_bytes = torch.cuda.get_device_properties(0).total_memory
        vram_gb = vram_bytes / (1024 ** 3)
        name = torch.cuda.get_device_name(0)
        return name, vram_gb
    except ImportError:
        return None, 0


def load_dataset():
    entries = []
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def main():
    print("JARVIS-MKIII Local Training Script")
    print("=" * 40)

    # Check dataset
    if not DATASET_PATH.exists():
        print(f"Error: Dataset not found at {DATASET_PATH}")
        sys.exit(1)

    entries = load_dataset()
    print(f"Dataset: {len(entries)} entries")

    # Check GPU
    gpu_name, vram_gb = check_gpu()
    if gpu_name is None:
        print("\nNo CUDA GPU detected.")
        print("Use Google Colab instead: training/colab_finetune.ipynb")
        sys.exit(1)

    print(f"GPU: {gpu_name} ({vram_gb:.1f} GB VRAM)")

    if vram_gb < MIN_VRAM_GB:
        print(f"\nInsufficient VRAM: {vram_gb:.1f} GB (need {MIN_VRAM_GB}+ GB)")
        print("Use Google Colab instead: training/colab_finetune.ipynb")
        sys.exit(1)

    print(f"VRAM check passed. Starting local training...\n")

    # Import training dependencies
    try:
        from unsloth import FastLanguageModel
        from trl import SFTTrainer
        from transformers import TrainingArguments
        from datasets import Dataset
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Install with: pip install unsloth trl transformers datasets")
        sys.exit(1)

    JARVIS_SYSTEM = (
        "You are JARVIS, an advanced AI assistant created by Khalid. "
        "You speak in a dry, clipped British tone. You always address the user as 'sir'. "
        "You never say 'certainly', 'of course', 'absolutely', 'sure', or 'great'. "
        "You keep responses concise — maximum 2 sentences for simple queries."
    )

    print("Loading base model (Llama-3.1-8B-Instruct, 4-bit)...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/Meta-Llama-3.1-8B-Instruct",
        max_seq_length=2048,
        load_in_4bit=True,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                         "gate_proj", "up_proj", "down_proj"],
        lora_alpha=32,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    def format_entry(entry):
        messages = [
            {"role": "system", "content": JARVIS_SYSTEM},
            {"role": "user", "content": entry["instruction"]},
            {"role": "assistant", "content": entry["response"]},
        ]
        return {"text": tokenizer.apply_chat_template(messages, tokenize=False)}

    raw_ds = Dataset.from_list(entries)
    dataset = raw_ds.map(format_entry)

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=2048,
        args=TrainingArguments(
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            num_train_epochs=3,
            learning_rate=2e-4,
            fp16=True,
            logging_steps=10,
            optim="adamw_8bit",
            output_dir=str(OUTPUT_PATH / "checkpoints"),
        ),
    )

    print("Training started...")
    trainer.train()

    model.save_pretrained(str(OUTPUT_PATH))
    tokenizer.save_pretrained(str(OUTPUT_PATH))
    print(f"\nAdapter saved to: {OUTPUT_PATH}")
    print("\nNext steps:")
    print("1. Convert to GGUF: python -m llama_cpp.convert_hf_to_gguf --outtype q4_k_m " + str(OUTPUT_PATH))
    print("2. Create Modelfile (see training/README.md)")
    print("3. Run: ollama create jarvis-mkiii -f Modelfile")


if __name__ == "__main__":
    main()
