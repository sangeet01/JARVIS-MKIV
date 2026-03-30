#!/bin/bash
# JARVIS-MKIII Retrain Script
set -e

DATASET="/home/k/JARVIS-MKIII/training/dataset.jsonl"
MIN_ENTRIES=200

if [ ! -f "$DATASET" ]; then
    echo "Error: Dataset not found at $DATASET"
    exit 1
fi

COUNT=$(wc -l < "$DATASET")
echo "Dataset size: $COUNT entries"

if [ "$COUNT" -lt "$MIN_ENTRIES" ]; then
    echo "Not enough data yet. Need ${MIN_ENTRIES}+ entries. Currently: $COUNT"
    echo "Keep using JARVIS to auto-collect more interactions."
    exit 1
fi

echo "Dataset ready for training (${COUNT} entries)."
echo ""
echo "Options:"
echo "  1. Google Colab (recommended): Upload training/dataset.jsonl to colab_finetune.ipynb"
echo "  2. Local GPU training: python training/local_train.py"
echo ""
echo "Colab notebook: training/colab_finetune.ipynb"
echo ""

# Check for local GPU
if command -v nvidia-smi &>/dev/null; then
    VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
    echo "GPU detected: ${VRAM}MB VRAM"
    if [ "$VRAM" -ge 8000 ]; then
        echo "Sufficient VRAM for local training."
        read -p "Run local training now? [y/N]: " choice
        if [[ "$choice" =~ ^[Yy]$ ]]; then
            python training/local_train.py
        fi
    else
        echo "Insufficient VRAM for 8B model. Use Google Colab instead."
    fi
else
    echo "No GPU detected. Use Google Colab for training."
fi
