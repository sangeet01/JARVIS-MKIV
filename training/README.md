# JARVIS-MKIII Training Pipeline

Complete guide to fine-tuning and deploying a custom JARVIS LLM.

## Overview

The training pipeline uses:
- **Base model**: Llama-3.1-8B-Instruct
- **Method**: LoRA (Low-Rank Adaptation) via Unsloth
- **Format**: GGUF Q4_K_M for local inference via Ollama
- **Dataset**: Auto-collected from live JARVIS interactions

## Dataset

### Current Stats
Check current dataset size:
```bash
wc -l training/dataset.jsonl
```

### Auto-Collection
The `/chat` endpoint automatically logs high-quality interactions to `dataset.jsonl`. Run JARVIS normally and the dataset grows on its own.

### Manual Addition
```python
from training.collector import log_training_pair
log_training_pair(
    prompt="What's the weather like?",
    response="Overcast with a 30% chance of rain, sir. Pack accordingly.",
    category="weather"
)
```

## Training on Google Colab

### Step 1: Open the Notebook
Upload `training/colab_finetune.ipynb` to Google Colab.

### Step 2: Upload Dataset
When prompted in the notebook, upload `training/dataset.jsonl`.

### Step 3: Run All Cells
The notebook will:
1. Install Unsloth + dependencies
2. Load Llama-3.1-8B-Instruct (4-bit quantized)
3. Apply LoRA adapters
4. Train for 3 epochs (~30-60 min on T4 GPU)
5. Export to GGUF Q4_K_M format
6. Download the model zip

### Training Requirements
- Google Colab with T4 GPU (free tier works)
- ~15GB VRAM required (4-bit quantization fits in 16GB)
- ~1 hour training time for 100-500 entries

## Local Training (GPU Required)

```bash
python training/local_train.py
```

Requires:
- NVIDIA GPU with 8GB+ VRAM
- CUDA 12.x
- Python 3.10+

## Installing in Ollama

### Step 1: Create Modelfile
```
FROM ./jarvis-mkiii-q4_k_m.gguf

SYSTEM """You are JARVIS, an advanced AI assistant created by Khalid.
You speak in a dry, clipped British tone.
You always address the user as 'sir'.
You never say 'certainly', 'of course', 'absolutely', 'sure', or 'great'.
You keep responses concise — maximum 2 sentences for simple queries."""

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
PARAMETER num_ctx 4096
```

Save as `Modelfile` in the same directory as the .gguf file.

### Step 2: Create Ollama Model
```bash
ollama create jarvis-mkiii -f Modelfile
```

### Step 3: Test
```bash
ollama run jarvis-mkiii "Who are you?"
```

Expected response: `JARVIS, sir. Your personal AI system, at your service.`

## Switching JARVIS to Local Model

In `backend/config/settings.py`, update:
```python
# Change from:
LLM_MODEL = "llama3.1:8b"  # or whatever current model

# To:
LLM_MODEL = "jarvis-mkiii"
```

Or set environment variable:
```bash
export JARVIS_LLM_MODEL=jarvis-mkiii
```

## Retraining

After collecting 200+ entries:

**Linux/Mac:**
```bash
bash training/retrain.sh
```

**Windows:**
```batch
training\retrain.bat
```

## Dataset Categories

| Category | Description | Target Count |
|----------|-------------|--------------|
| identity | Who JARVIS is, who Khalid is | 12+ |
| system | App launches, OS control | 15+ |
| calendar | Schedule and time queries | 10+ |
| weather | Weather queries | 8+ |
| memory | Memory storage/recall | 8+ |
| analysis | Reasoning, summaries | 12+ |
| dry_wit | Humor and personality | 10+ |
| arabic | Arabic language support | 8+ |
| briefing | Daily/morning briefings | 10+ |
| error | Error handling responses | 7+ |
