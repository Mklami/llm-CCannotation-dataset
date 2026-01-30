# LLM Code Clone Detection Dataset

This repository contains a dataset of labeled patch pairs for code clone detection, specifically designed for training and evaluating Large Language Models (LLMs) on identifying code clones in automated program repair patches.

## Overview

The dataset consists of pairs of code patches from the Defects4J benchmark, where each pair has been manually labeled by experts to indicate the type of relationship (clone type) between the two patches. This dataset is designed for code clone detection tasks, where the goal is to identify whether two patches are clones (similar fixes) or not.

## Dataset Structure

### Files

- **`labeled_pairs.csv`**: Main dataset file containing all labeled patch pairs
- **`labeled_pairs_train.csv`**: Training split (project-based)
- **`labeled_pairs_test.csv`**: Test split (project-based)
- **`patches/`**: Directory containing all patch files referenced in the CSV files

### CSV Format

The CSV files have three columns:

| Column | Description | Example |
|--------|-------------|---------|
| `uid` | Unique identifier for the first patch in the pair | `aprenfl-defects4j-Math-11-TBar-Patch_31_8` |
| `groundtruth_index` | Unique identifier for the second patch in the pair | `defects4j-Math-11-developer` |
| `expert_label` | Expert-annotated relationship type between the patches | `type-3` |

### Patch Naming Convention

Patch filenames follow this pattern:
```
{source}-defects4j-{Project}-{BugID}-{Tool}-{Identifier}.patch
```

**Components:**
- **`source`**: Dataset or repository source (e.g., `aprenfl`, `historian`, `dl4pc2`, `drr`)
- **`defects4j`**: Indicates patches are from the Defects4J benchmark
- **`Project`**: Project name (e.g., `Chart`, `Math`, `Lang`, `Closure`, `Cli`)
- **`BugID`**: Bug identifier number (e.g., `1`, `11`, `82`)
- **`Tool`**: Automated repair tool that generated the patch (e.g., `TBar`, `Arja`, `SimFix`, `developer`)
- **`Identifier`**: Additional identifier (patch number, variant, etc.)

**Examples:**
- `aprenfl-defects4j-Math-11-TBar-Patch_31_8.patch` - TBar patch for Math bug #11
- `defects4j-Math-11-developer.patch` - Developer (ground truth) patch for Math bug #11
- `historian-defects4j-Chart-1-rapgen-14.patch` - RapGen patch for Chart bug #1

### Patch File Format

Patch files are in standard unified diff format:
```diff
--- a/path/to/file.java
+++ b/path/to/file.java
@@ -line_num,count +line_num,count @@
- old code
+ new code
```

## Expert Labels

The `expert_label` column indicates the relationship type between two patches:

| Label | Description | Count |
|-------|-------------|-------|
| **`type-1`** | Exact clones - Identical patches | 329 |
| **`type-2`** | Near-exact clones - Very similar with minor differences | 23 |
| **`type-3`** | Functional clones - Different implementations, same fix | 2,250 |
| **`type-4`** | Semantic clones - Similar intent, different approach | 91 |
| **`not-clone`** | Not clones - Different fixes for the same bug | 1,497 |
| **(empty)** | Unlabeled pairs | 58 |

**Clone Type Hierarchy:**
- **Type-1** (Exact): Patches are identical
- **Type-2** (Near-exact): Patches differ only in formatting, variable names, or trivial changes
- **Type-3** (Functional): Patches implement the same fix using different code structures
- **Type-4** (Semantic): Patches address the same bug but with different approaches
- **Not-clone**: Patches fix the same bug but in fundamentally different ways

## Dataset Statistics

- **Total pairs**: 4,248
- **Training pairs**: ~2,069 (project-based split)
- **Test pairs**: ~2,183 (project-based split)
- **Total patches**: 65,344 unique patch files
- **Projects**: Chart, Math, Lang, Closure, Cli, Jsoup, Codec, JacksonCore, JacksonDatabind, and more

## Usage

### Loading the Dataset

```python
import csv

# Load labeled pairs
pairs = []
with open('labeled_pairs.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        pairs.append(row)

# Access a pair
pair = pairs[0]
print(f"Patch 1: {pair['uid']}")
print(f"Patch 2: {pair['groundtruth_index']}")
print(f"Label: {pair['expert_label']}")
```

### Reading Patch Files

```python
from pathlib import Path

patches_dir = Path('patches')

# Read patch content
patch1_name = pairs[0]['uid']
patch1_path = patches_dir / f"{patch1_name}.patch"

with open(patch1_path, 'r') as f:
    patch1_content = f.read()
```

### Working with Train/Test Splits

The dataset includes pre-split train/test files based on projects to ensure complete separation:

```python
# Load training data
train_pairs = []
with open('labeled_pairs_train.csv', 'r') as f:
    reader = csv.DictReader(f)
    train_pairs = list(reader)

# Load test data
test_pairs = []
with open('labeled_pairs_test.csv', 'r') as f:
    reader = csv.DictReader(f)
    test_pairs = list(reader)
```

## Dataset Creation

### Deduplication

The dataset has been deduplicated to avoid duplicate bug solutions. The deduplication process:
- Groups pairs by **bug ID** (Project-BugID combination)
- Groups by **modified methods** (files are ignored - same files can have different method modifications)
- Keeps only one pair per unique combination

This ensures that if patch A and patch B are compared, you won't have patch C and patch D that modify the same methods for the same bug.

### Project-Based Split

The train/test split is **project-based**, meaning:
- Entire projects are assigned to either train OR test
- No project appears in both splits
- Ensures no data leakage between train and test sets


