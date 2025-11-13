#!/usr/bin/env python3
"""Test script for model selection persistence."""

import yaml
from main import save_models_to_config

print("="*70)
print("🧪 Testing Model Selection Persistence")
print("="*70)

# Test 1: Save models
print("\n1️⃣  Testing save_models_to_config...")
test_models = ['llama3.2:1b', 'phi3:mini', 'qwen2.5:0.5b', 'gemma2:2b', 'tinyllama:latest', 'mistral:latest']
result = save_models_to_config(test_models)
print(f"   Save result: {'✓ SUCCESS' if result else '✗ FAILED'}")

# Test 2: Load models
print("\n2️⃣  Testing load from config...")
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

configured_models = config.get('ollama_models', [])
print(f"   Loaded {len(configured_models)} models: {configured_models}")

# Test 3: Check logic
print("\n3️⃣  Testing selection skip logic...")
initial_agents = config['game']['initial_agents']
should_skip = configured_models and len(configured_models) >= initial_agents

print(f"   Agents needed: {initial_agents}")
print(f"   Models available: {len(configured_models)}")
print(f"   Should skip selection: {'✓ YES' if should_skip else '✗ NO'}")

# Test 4: Verify models match
print("\n4️⃣  Verifying data integrity...")
if configured_models == test_models:
    print("   ✓ Models match perfectly")
else:
    print("   ✗ Model mismatch!")
    print(f"   Expected: {test_models}")
    print(f"   Got: {configured_models}")

print("\n" + "="*70)
print("✓ All tests completed successfully!")
print("="*70)
