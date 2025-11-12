#!/usr/bin/env python3
"""Test script to verify model selection workflow."""

from utils.gpu_utils import gpu_manager
from utils.model_selector import select_models_cli

# Get GPU info
gpu_info = gpu_manager.get_info()
gpu_capacity = gpu_manager.estimate_model_capacity()

print("="*80)
print("GPU INFORMATION")
print("="*80)
print(f"Available: {gpu_info['available']}")
print(f"Name: {gpu_info['name']}")
print(f"Memory: {gpu_info['memory_gb']:.2f} GB" if gpu_info['memory_gb'] else "N/A")
print(f"Max Models: {gpu_capacity['max_models']}")
print()

# Test model selection
gpu_memory = gpu_info['memory_gb'] if gpu_info['available'] else 4.0
selected_models = select_models_cli(gpu_memory, 6)

print("\n" + "="*80)
print("SELECTED MODELS")
print("="*80)
for i, model in enumerate(selected_models, 1):
    print(f"{i}. {model}")
print()
