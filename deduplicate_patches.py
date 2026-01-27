#!/usr/bin/env python3
"""
Balanced stratified split - aims for target train/test PAIR percentages.
"""

import csv
import re
import os
import random
from collections import defaultdict
from pathlib import Path


def extract_bug_id(patch_name):
    """Extract bug ID (Project-BugID) from patch filename."""
    match = re.search(r'defects4j-([A-Za-z]+-\d+)', patch_name)
    if match:
        return match.group(1)
    return None


def parse_patch_file(patch_path):
    """Parse a patch file to extract modified files and methods."""
    if not os.path.exists(patch_path):
        return set(), set(), set()
    
    modified_files = set()
    modified_methods = set()
    file_method_pairs = set()
    
    try:
        with open(patch_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        current_file = None
        file_pattern = r'^[+-]{3} [ab]/(.+)$'
        
        for line in content.split('\n'):
            match = re.match(file_pattern, line)
            if match:
                file_path = match.group(1)
                if file_path.endswith('.java'):
                    current_file = file_path
                    modified_files.add(file_path)
            
            if line.startswith('@@') and current_file:
                method_match = re.search(r'@@.*@@\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', line)
                if method_match:
                    method_name = method_match.group(1)
                    modified_methods.add(method_name)
                    file_method_pairs.add((current_file, method_name))
            
            if current_file and (line.startswith('+') or line.startswith('-') or line.startswith(' ')):
                clean_line = line[1:].strip() if line else ''
                
                method_patterns = [
                    r'^\s*(?:public|private|protected|static|final|synchronized|native|abstract|\s)+[\w<>\[\],\s]+\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*(?:throws\s+[\w\s,]+)?\s*\{?',
                    r'^\s*(?:public|private|protected)\s+([A-Z][a-zA-Z0-9_]*)\s*\(',
                    r'^\s*(?:public|private|protected|static|final|\s)+\s*<[^>]+>\s*\w+\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',
                ]
                
                for pattern in method_patterns:
                    method_match = re.search(pattern, clean_line)
                    if method_match:
                        method_name = method_match.group(1)
                        if method_name not in ['if', 'for', 'while', 'switch', 'catch', 'try', 
                                               'else', 'return', 'new', 'class', 'interface']:
                            modified_methods.add(method_name)
                            file_method_pairs.add((current_file, method_name))
                            break
    
    except Exception as e:
        print(f"Warning: Could not parse patch {patch_path}: {e}")
    
    return modified_files, modified_methods, file_method_pairs


def extract_class_name(file_path):
    """Extract class name from file path."""
    if '/' in file_path:
        return file_path.split('/')[-1].replace('.java', '')
    return file_path.replace('.java', '')


def create_signature(patch1_files, patch1_file_methods, patch2_files, patch2_file_methods, 
                     granularity='class'):
    """Create signature with fallback logic."""
    
    all_file_methods = patch1_file_methods | patch2_file_methods
    
    if all_file_methods:
        if granularity == 'method':
            methods = set(m for _, m in all_file_methods)
            return tuple(sorted(methods))
        elif granularity == 'class':
            class_methods = set(f"{extract_class_name(f)}::{m}" for f, m in all_file_methods)
            return tuple(sorted(class_methods))
        elif granularity == 'file':
            return tuple(sorted(all_file_methods))
    
    all_files = patch1_files | patch2_files
    if all_files:
        if granularity in ['class', 'method']:
            classes = set(extract_class_name(f) for f in all_files)
            return tuple(sorted(classes))
        else:
            return tuple(sorted(all_files))
    
    return tuple()


def create_balanced_split(signature_to_pairs, train_ratio=0.7, max_per_signature=None):
    """
    Create balanced train/test split aiming for target PAIR percentages.
    
    Ensures:
    1. No signature appears in both train and test
    2. Train/test ratio is close to target (in terms of pairs, not signatures)
    """
    
    # Calculate totals
    total_pairs_before_limit = sum(len(pairs) for pairs in signature_to_pairs.values())
    
    # Apply max_per_signature and collect pairs with signatures
    signature_pair_lists = {}
    total_pairs_after_limit = 0
    
    for signature, pair_list in signature_to_pairs.items():
        if max_per_signature and len(pair_list) > max_per_signature:
            sampled = random.sample(pair_list, max_per_signature)
        else:
            sampled = pair_list
        signature_pair_lists[signature] = sampled
        total_pairs_after_limit += len(sampled)
    
    # Sort signatures by size (descending) for better balance
    sorted_sigs = sorted(
        signature_pair_lists.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )
    
    # Greedy assignment to achieve target ratio
    target_train_count = int(total_pairs_after_limit * train_ratio)
    train_pairs = []
    test_pairs = []
    train_sigs = []
    test_sigs = []
    
    for signature, pair_list in sorted_sigs:
        # Add to train if we haven't reached target, otherwise test
        if len(train_pairs) < target_train_count:
            train_pairs.extend([item['pair'] for item in pair_list])
            train_sigs.append(signature)
        else:
            test_pairs.extend([item['pair'] for item in pair_list])
            test_sigs.append(signature)
    
    print(f"\nBalanced Stratified Split:")
    print(f"  Total signatures: {len(sorted_sigs)}")
    print(f"  Train signatures: {len(train_sigs)} ({len(train_sigs)/len(sorted_sigs)*100:.1f}%)")
    print(f"  Test signatures: {len(test_sigs)} ({len(test_sigs)/len(sorted_sigs)*100:.1f}%)")
    print(f"\n  Target split: {train_ratio*100:.0f}% train / {(1-train_ratio)*100:.0f}% test")
    print(f"  Actual split: {len(train_pairs)/total_pairs_after_limit*100:.1f}% train / {len(test_pairs)/total_pairs_after_limit*100:.1f}% test")
    print(f"  Target train pairs: {target_train_count}")
    print(f"  Actual train pairs: {len(train_pairs)}")
    print(f"  Difference: {abs(len(train_pairs) - target_train_count)} pairs")
    
    return train_pairs, test_pairs


def main():
    patches_dir = Path('patches')
    csv_file = 'labeled_pairs.csv'
    
    GRANULARITY = 'class'
    TRAIN_RATIO = 0.3          # 30% train, 70% test (like the paper)
    MAX_PER_SIGNATURE = None
    RANDOM_SEED = 42
    
    random.seed(RANDOM_SEED)
    
    print("="*70)
    print("BALANCED STRATIFIED TRAIN/TEST SPLIT")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Granularity: {GRANULARITY}")
    print(f"  Target Train/Test ratio: {TRAIN_RATIO:.0%} / {1-TRAIN_RATIO:.0%}")
    print(f"  Max per signature: {MAX_PER_SIGNATURE if MAX_PER_SIGNATURE else 'unlimited'}")
    print(f"  Random seed: {RANDOM_SEED}")
    
    print(f"\nReading {csv_file}...")
    pairs = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pairs.append(row)
    
    print(f"Found {len(pairs)} pairs")
    
    print("\nParsing patches...")
    signature_to_pairs = defaultdict(list)
    patch_cache = {}
    
    for idx, pair in enumerate(pairs):
        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx + 1}/{len(pairs)}...")
        
        uid = pair['uid']
        groundtruth = pair['groundtruth_index']
        
        bug_id1 = extract_bug_id(uid)
        bug_id2 = extract_bug_id(groundtruth)
        
        if bug_id1 != bug_id2:
            continue
        
        if uid not in patch_cache:
            patch1_path = patches_dir / f"{uid}.patch"
            patch_cache[uid] = parse_patch_file(patch1_path)
        
        if groundtruth not in patch_cache:
            patch2_path = patches_dir / f"{groundtruth}.patch"
            patch_cache[groundtruth] = parse_patch_file(patch2_path)
        
        patch1_files, _, patch1_file_methods = patch_cache[uid]
        patch2_files, _, patch2_file_methods = patch_cache[groundtruth]
        
        signature = create_signature(
            patch1_files, patch1_file_methods,
            patch2_files, patch2_file_methods,
            granularity=GRANULARITY
        )
        
        signature_to_pairs[signature].append({
            'pair': pair,
            'bug_id': bug_id1
        })
    
    print(f"\nFound {len(signature_to_pairs)} unique signatures")
    
    # Create balanced split
    train_pairs, test_pairs = create_balanced_split(
        signature_to_pairs,
        train_ratio=TRAIN_RATIO,
        max_per_signature=MAX_PER_SIGNATURE
    )
    
    print("\n" + "="*70)
    print("FINAL RESULTS")
    print("="*70)
    print(f"Train pairs: {len(train_pairs)}")
    print(f"Test pairs: {len(test_pairs)}")
    print(f"Total: {len(train_pairs) + len(test_pairs)}")
    
    # Write outputs
    with open('labeled_pairs_train.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['uid', 'groundtruth_index', 'expert_label'])
        writer.writeheader()
        writer.writerows(train_pairs)
    
    with open('labeled_pairs_test.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['uid', 'groundtruth_index', 'expert_label'])
        writer.writeheader()
        writer.writerows(test_pairs)
    
    print(f"\n✓ Done! Files written.")


if __name__ == '__main__':
    main()
