#!/usr/bin/env python
"""
Quick sanity test without API calls
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ml_engineer.agent import MLEngineerAgent
from ml_engineer.datasets import DatasetResolver

print("Testing ML Engineer Agent setup...")

# Test 1: Agent initialization
print("\n1. Testing agent initialization...")
try:
    agent = MLEngineerAgent(dataset_path="sample_sales", max_iterations=5)
    print(f"   ✓ Agent created successfully")
    print(f"   ✓ Dataset: {agent.dataset_name}")
    print(f"   ✓ Model: {agent.model_name}")
    print(f"   ✓ Tools: {len(agent.tools)}")
    path_vars = agent.get_dataset_path_variables()
    assert "DATASET_PATH" in path_vars
    print(f"   ✓ Dataset path variable injected: {path_vars['DATASET_PATH']}")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test 2: System prompt generation
print("\n2. Testing system prompt generation...")
try:
    prompt = agent._create_system_prompt()
    print(f"   ✓ System prompt created ({len(prompt)} characters)")
    assert "dataset" in prompt.lower()
    assert "ml" in prompt.lower() or "machine learning" in prompt.lower()
    print(f"   ✓ Prompt contains expected keywords")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test 3: Workflow setup
print("\n3. Testing workflow setup...")
try:
    agent._setup_workflow()
    print(f"   ✓ Workflow configured")
    assert agent.app is not None
    print(f"   ✓ App compiled successfully")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("✅ All quick tests passed!")
print("="*60)
print("\nThe agent is properly configured.")
print("To run with real data, use:")
print("  python usage.py --prompt 'Your task' --dataset sample_sales")
print()