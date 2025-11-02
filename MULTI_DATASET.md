# Multiple Dataset Support

## Overview

The ML Engineer Agent now supports working with **multiple datasets simultaneously**! This is perfect for train/test splits or combining related datasets.

## Usage

### Quick Example

```python
from ml_engineer.agent import MLEngineerAgent

# Use multiple datasets
agent = MLEngineerAgent(
    dataset_path=["office_train", "office_test"],  # List of datasets
    verbose=True,
    planning_mode=True
)

result = agent.run("""
Build a classification model:
1. Train on office_train
2. Test on office_test
3. Evaluate performance
""")
```

### CLI Usage

For CLI, you can still use single datasets:
```bash
python usage.py --prompt "Analyze data" --dataset office_train
```

For multiple datasets, use the programmatic API (example_run.py).

## How It Works

### Single Dataset (Old Behavior)

```python
agent = MLEngineerAgent(dataset_path="sample_sales")

# In code, access as:
# df - the dataset
# DATASET_PATH - path to dataset
```

### Multiple Datasets (New!)

```python
agent = MLEngineerAgent(dataset_path=["office_train", "office_test"])

# In code, access as:
# df_office_train - training dataset
# df_office_test - test dataset
# DATASET_PATH_OFFICE_TRAIN - path to train
# DATASET_PATH_OFFICE_TEST - path to test
```

## Variable Naming Convention

For multiple datasets, variables are named: `df_{dataset_name}`

Examples:
- `office_train.csv` → `df_office_train`
- `office_test.csv` → `df_office_test`
- `sample_sales.csv` → `df_sample_sales`

## Example: Train/Test Split

```python
agent = MLEngineerAgent(
    dataset_path=["office_train", "office_test"],
    model_name="gpt-5",
    reasoning_effort="high"
)

result = agent.run("""
Build a complete ML pipeline:
1. Explore df_office_train structure
2. Train a model on df_office_train
3. Evaluate on df_office_test
4. Compare training vs test performance
5. Provide model insights
""")
```

## System Prompt (Multiple Datasets)

When using multiple datasets, the agent receives:

```
**Multiple Datasets Available:**
- office_train: /path/to/office_train.csv
- office_test: /path/to/office_test.csv

You have access to multiple datasets. They are loaded as:
- df_office_train = office_train dataset
- df_office_test = office_test dataset
```

## Code Examples

### Training on One, Testing on Another

```python
# Agent can write code like this:
from sklearn.ensemble import RandomForestClassifier

# Train on training data
X_train = df_office_train.drop('target', axis=1)
y_train = df_office_train['target']

model = RandomForestClassifier()
model.fit(X_train, y_train)

# Test on test data
X_test = df_office_test.drop('target', axis=1)
y_test = df_office_test['target']

predictions = model.predict(X_test)
accuracy = accuracy_score(y_test, predictions)
print(f"Test Accuracy: {accuracy}")
```

### Comparing Datasets

```python
# Compare distributions
print("Train dataset shape:", df_office_train.shape)
print("Test dataset shape:", df_office_test.shape)

# Compare statistics
print("\nTrain stats:")
print(df_office_train.describe())

print("\nTest stats:")
print(df_office_test.describe())

# Check for distribution drift
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 2, figsize=(12, 4))

df_office_train['feature'].hist(ax=axes[0], alpha=0.7)
axes[0].set_title('Train Distribution')

df_office_test['feature'].hist(ax=axes[1], alpha=0.7)
axes[1].set_title('Test Distribution')

plt.show()
```

## Built-in Dataset Pairs

Available in catalog:
- `office_train` + `office_test` (office dataset split)
- `sample_sales` (single dataset)
- `xau_intraday` (single dataset)

## Artifacts

When using multiple datasets, artifacts are named with combined names:

```
artifacts/
└── 20241102_143022_office_train_office_test/
    ├── plot_001.png
    ├── plot_002.png
    └── office_train_office_test_pipeline.ipynb
```

## Verbose Output

```
🚀 ML ENGINEER AGENT STARTING
═══════════════════════════════
Dataset: office_train_office_test
Model: gpt-5

   Loaded office_train: 50000 rows × 10 columns
   Loaded office_test: 10000 rows × 10 columns
```

## Use Cases

### 1. Train/Test Split

```python
agent = MLEngineerAgent(
    dataset_path=["train_data", "test_data"]
)

agent.run("Train on df_train_data, test on df_test_data")
```

### 2. Validation Sets

```python
agent = MLEngineerAgent(
    dataset_path=["train", "validation", "test"]
)

agent.run("""
Train on df_train
Tune hyperparameters on df_validation
Final evaluation on df_test
""")
```

### 3. Time-based Splits

```python
agent = MLEngineerAgent(
    dataset_path=["data_2022", "data_2023", "data_2024"]
)

agent.run("""
Train on df_data_2022 and df_data_2023
Test on df_data_2024 (future data)
""")
```

### 4. Data Comparison

```python
agent = MLEngineerAgent(
    dataset_path=["version1", "version2"]
)

agent.run("""
Compare df_version1 and df_version2
Show differences in distributions
Identify data quality issues
""")
```

## Example Run

```bash
$ python example_run.py

ML Engineer Agent - Programmatic Example
================================================================================

Task: Build a complete ML pipeline using office_train and office_test
Datasets: office_train, office_test

🚀 ML ENGINEER AGENT STARTING
════════════════════════════════════════

Run ID: 20241102_143022_office_train_office_test
Dataset: office_train_office_test
Model: gpt-5
Reasoning Effort: high

   Loaded office_train: 50000 rows × 10 columns
   Loaded office_test: 10000 rows × 10 columns

📋 PLAN
════════════════════════════════════════
1. Explore both datasets
2. Train model on office_train
3. Test on office_test
4. Evaluate and compare
...
```

## Tips

1. **Use descriptive names**: `train`, `test`, `validation` are clear
2. **Same schema**: Datasets should have compatible schemas
3. **Mention in prompt**: Tell the agent which dataset to use for what
4. **Check distributions**: Compare train/test distributions for drift

## Limitations

- CLI only supports single dataset (use programmatic API for multiple)
- All datasets loaded into memory at once
- Dataset names combined for artifact paths

## Migration from Single Dataset

**Before (single)**:
```python
agent = MLEngineerAgent(dataset_path="data.csv")
# Access: df
```

**After (multiple)**:
```python
agent = MLEngineerAgent(dataset_path=["train.csv", "test.csv"])
# Access: df_train, df_test
```

**Still works (backward compatible)**:
```python
agent = MLEngineerAgent(dataset_path="data.csv")
# Still access: df (no change!)
```

## Summary

✅ **Single dataset**: `dataset_path="name"` → access as `df`
✅ **Multiple datasets**: `dataset_path=["name1", "name2"]` → access as `df_name1`, `df_name2`
✅ **Backward compatible**: Old code still works
✅ **Perfect for train/test splits**
✅ **All datasets available simultaneously**

Try it now:
```bash
python example_run.py
```

This will run with office_train and office_test datasets! 🚀
