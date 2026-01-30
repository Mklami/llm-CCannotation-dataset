#!/usr/bin/env python3
"""
Project-based train/test split for code clone detection.
Ensures complete separation: entire projects go to train OR test.
"""

import csv
import re
from collections import defaultdict
from pathlib import Path


def extract_project_and_bug(patch_name):
    """Extract project name and bug ID from patch filename.
    
    Example: 'historian-defects4j-Chart-1-rapgen-14.patch' 
             -> ('Chart', 'Chart-1')
    """
    match = re.search(r'defects4j-([A-Za-z]+)-(\d+)', patch_name)
    if match:
        project = match.group(1)
        bug_id = f"{project}-{match.group(2)}"
        return project, bug_id
    return None, None


def main():
    csv_file = 'labeled_pairs.csv'
    
    print("="*70)
    print("PROJECT-BASED TRAIN/TEST SPLIT")
    print("="*70)
    
    # Read all pairs
    print(f"\nReading {csv_file}...")
    pairs = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pairs.append(row)
    
    print(f"Found {len(pairs)} pairs")
    
    # Group pairs by project
    print("\nGrouping pairs by project...")
    project_to_pairs = defaultdict(list)
    
    for pair in pairs:
        project, bug_id = extract_project_and_bug(pair['uid'])
        if project:
            project_to_pairs[project].append(pair)
    
    # Show project statistics
    print(f"\nProject distribution:")
    print(f"{'Project':<15} {'Pairs':>8} {'Bugs':>8}")
    print("-" * 35)
    
    project_stats = []
    for project, project_pairs in sorted(project_to_pairs.items()):
        bugs = set()
        for pair in project_pairs:
            _, bug_id = extract_project_and_bug(pair['uid'])
            bugs.add(bug_id)
        
        project_stats.append({
            'project': project,
            'pairs': len(project_pairs),
            'bugs': len(bugs)
        })
        print(f"{project:<15} {len(project_pairs):>8} {len(bugs):>8}")
    
    total_pairs = sum(s['pairs'] for s in project_stats)
    print("-" * 35)
    print(f"{'TOTAL':<15} {total_pairs:>8}")
    
    # Sort projects by size (number of pairs)
    project_stats.sort(key=lambda x: x['pairs'], reverse=True)
    
    print("\n" + "="*70)
    print("RECOMMENDED SPLITS")
    print("="*70)
    
    # Strategy 1: Largest projects to test (realistic - test on big projects)
    print("\nOption 1: Largest projects → Test (recommended)")
    print("-" * 70)
    
    target_test_ratio = 0.7  # 70% to test (like the paper - small gold set)
    target_test_pairs = int(total_pairs * target_test_ratio)
    
    test_projects = []
    train_projects = []
    test_pair_count = 0
    
    # Greedy: add largest projects to test until we hit target
    for stat in project_stats:
        if test_pair_count < target_test_pairs:
            test_projects.append(stat['project'])
            test_pair_count += stat['pairs']
        else:
            train_projects.append(stat['project'])
    
    train_pair_count = total_pairs - test_pair_count
    
    print(f"\nTrain projects ({len(train_projects)}): {', '.join(sorted(train_projects))}")
    print(f"Test projects ({len(test_projects)}): {', '.join(sorted(test_projects))}")
    print(f"\nTrain pairs: {train_pair_count} ({train_pair_count/total_pairs*100:.1f}%)")
    print(f"Test pairs: {test_pair_count} ({test_pair_count/total_pairs*100:.1f}%)")
    
    # Strategy 2: Smallest projects to test (easier test set)
    print("\n" + "-"*70)
    print("Option 2: Smallest projects → Test (easier)")
    print("-" * 70)
    
    test_projects_alt = []
    train_projects_alt = []
    test_pair_count_alt = 0
    
    # Reverse: add smallest projects to test
    for stat in reversed(project_stats):
        if test_pair_count_alt < target_test_pairs:
            test_projects_alt.append(stat['project'])
            test_pair_count_alt += stat['pairs']
        else:
            train_projects_alt.append(stat['project'])
    
    train_pair_count_alt = total_pairs - test_pair_count_alt
    
    print(f"\nTrain projects ({len(train_projects_alt)}): {', '.join(sorted(train_projects_alt))}")
    print(f"Test projects ({len(test_projects_alt)}): {', '.join(sorted(test_projects_alt))}")
    print(f"\nTrain pairs: {train_pair_count_alt} ({train_pair_count_alt/total_pairs*100:.1f}%)")
    print(f"Test pairs: {test_pair_count_alt} ({test_pair_count_alt/total_pairs*100:.1f}%)")
    
    # Ask user to choose
    print("\n" + "="*70)
    choice = input("\nWhich split do you want? (1/2/custom): ").strip()
    
    if choice == '1':
        final_train_projects = set(train_projects)
        final_test_projects = set(test_projects)
    elif choice == '2':
        final_train_projects = set(train_projects_alt)
        final_test_projects = set(test_projects_alt)
    else:
        # Custom split
        print("\nEnter test projects (comma-separated):")
        print("Available:", ', '.join([s['project'] for s in project_stats]))
        test_input = input("Test projects: ").strip()
        final_test_projects = set(p.strip() for p in test_input.split(','))
        final_train_projects = set(project_to_pairs.keys()) - final_test_projects
    
    # Create train/test splits
    train_pairs = []
    test_pairs = []
    
    for project, project_pairs in project_to_pairs.items():
        if project in final_train_projects:
            train_pairs.extend(project_pairs)
        elif project in final_test_projects:
            test_pairs.extend(project_pairs)
    
    # Write outputs
    print("\n" + "="*70)
    print("WRITING FILES")
    print("="*70)
    
    with open('labeled_pairs_train.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['uid', 'groundtruth_index', 'expert_label'])
        writer.writeheader()
        writer.writerows(train_pairs)
    
    with open('labeled_pairs_test.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['uid', 'groundtruth_index', 'expert_label'])
        writer.writeheader()
        writer.writerows(test_pairs)
    
    print(f"\nFinal split:")
    print(f"  Train projects: {sorted(final_train_projects)}")
    print(f"  Test projects: {sorted(final_test_projects)}")
    print(f"  Train pairs: {len(train_pairs)}")
    print(f"  Test pairs: {len(test_pairs)}")
    print(f"\n✓ Files written!")
    print(f"  - labeled_pairs_train.csv")
    print(f"  - labeled_pairs_test.csv")


if __name__ == '__main__':
    main()
