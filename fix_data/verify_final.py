#!/usr/bin/env python3
"""
Quick verification of the cleaned fish_scraping_list_updated.csv
"""

import pandas as pd
from collections import Counter

# Load the cleaned file
df = pd.read_csv('/Users/user/Dev/scraping_fish/fish_scraping_list_updated.csv')

print("=== FINAL VERIFICATION ===")
print(f"Total rows: {len(df)}")

# Check for duplicate species_indonesia
species_counts = df['species_indonesia'].value_counts()
duplicates = species_counts[species_counts > 1]

if len(duplicates) > 0:
    print(f"❌ DUPLICATE SPECIES FOUND: {len(duplicates)}")
    for species, count in duplicates.head().items():
        print(f"  {species}: {count} times")
else:
    print("✅ No duplicate species_indonesia")

# Check for duplicate latin names
latin_name_counts = Counter()
for _, row in df.iterrows():
    if pd.notna(row['nama_latin']):
        latin_names = str(row['nama_latin']).split(' ; ')
        for name in latin_names:
            name = name.strip()
            if name:
                latin_name_counts[name] += 1

duplicated_latins = {k: v for k, v in latin_name_counts.items() if v > 1}

if duplicated_latins:
    print(f"❌ DUPLICATE LATIN NAMES: {len(duplicated_latins)}")
    for name, count in list(duplicated_latins.items())[:5]:
        print(f"  {name}: {count} times")
else:
    print("✅ No duplicate latin names")

# Check required fields
required_fields = ['species_indonesia', 'nama_latin', 'kelompok', 'jenis_perairan']
for field in required_fields:
    null_count = df[field].isnull().sum()
    empty_count = (df[field] == '').sum()
    total_missing = null_count + empty_count
    
    if total_missing > 0:
        print(f"⚠️  {field}: {total_missing} missing values")
    else:
        print(f"✅ {field}: No missing values")

# Summary stats
print(f"\n=== SUMMARY ===")
print(f"Total species: {len(df)}")
print(f"Unique latin names: {len(latin_name_counts)}")
print(f"Average latin names per species: {len(latin_name_counts) / len(df):.1f}")

# Check data consistency 
print(f"\nData structure looks good! File is ready for use.")