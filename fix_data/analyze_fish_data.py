#!/usr/bin/env python3
"""
Script to analyze and fix fish_scraping_list_updated.csv based on ikan_db.csv
- Check for field consistency 
- Remove duplicated latin names
- Merge entries with same Indonesian species names
"""

import pandas as pd
import re
from collections import defaultdict

def normalize_latin_name(latin_name):
    """Normalize latin name by removing extra spaces and standardizing format"""
    if pd.isna(latin_name) or latin_name == '':
        return ''
    # Split by semicolon and clean each part
    names = [name.strip() for name in str(latin_name).split(';')]
    # Remove empty names and duplicates while preserving order
    unique_names = []
    seen = set()
    for name in names:
        if name and name not in seen:
            unique_names.append(name)
            seen.add(name)
    return ' ; '.join(unique_names)

def load_and_analyze():
    # Load both files
    print("Loading files...")
    
    try:
        ikan_db = pd.read_csv('/Users/user/Dev/scraping_fish/ikan_db.csv')
        print(f"ikan_db.csv loaded: {len(ikan_db)} rows")
        print("ikan_db.csv columns:", list(ikan_db.columns))
    except Exception as e:
        print(f"Error loading ikan_db.csv: {e}")
        return
    
    try:
        fish_scraping = pd.read_csv('/Users/user/Dev/scraping_fish/fish_scraping_list_updated.csv')
        print(f"fish_scraping_list_updated.csv loaded: {len(fish_scraping)} rows")
        print("fish_scraping_list_updated.csv columns:", list(fish_scraping.columns))
    except Exception as e:
        print(f"Error loading fish_scraping_list_updated.csv: {e}")
        return
    
    # Compare field structures
    print("\n=== FIELD COMPARISON ===")
    scraping_fields = set(fish_scraping.columns)
    db_fields = set(ikan_db.columns)
    
    print("Fields in scraping but not in db:", scraping_fields - db_fields)
    print("Fields in db but not in scraping:", db_fields - scraping_fields)
    print("Common fields:", scraping_fields & db_fields)
    
    # Analyze latin names from ikan_db
    print("\n=== IKAN_DB LATIN NAMES ===")
    db_latin_names = set()
    for nama_latin in ikan_db['nama_latin'].dropna():
        if nama_latin:
            db_latin_names.add(str(nama_latin).strip())
    
    print(f"Unique latin names in ikan_db: {len(db_latin_names)}")
    
    # Check for duplicates in fish_scraping
    print("\n=== ANALYZING DUPLICATES IN FISH SCRAPING ===")
    
    # Normalize latin names first
    fish_scraping['nama_latin_normalized'] = fish_scraping['nama_latin'].apply(normalize_latin_name)
    
    # Find duplicate latin names
    latin_name_counts = defaultdict(list)
    for idx, row in fish_scraping.iterrows():
        latin_names = str(row['nama_latin_normalized']).split(' ; ') if row['nama_latin_normalized'] else ['']
        for latin_name in latin_names:
            latin_name = latin_name.strip()
            if latin_name:
                latin_name_counts[latin_name].append({
                    'index': idx,
                    'species_indonesia': row['species_indonesia'],
                    'row': row
                })
    
    duplicated_latins = {k: v for k, v in latin_name_counts.items() if len(v) > 1}
    print(f"Duplicated latin names found: {len(duplicated_latins)}")
    
    for latin_name, entries in duplicated_latins.items():
        print(f"\nLatin name '{latin_name}' appears in:")
        for entry in entries:
            print(f"  - Row {entry['index']}: {entry['species_indonesia']}")
    
    # Find duplicate Indonesian species names
    print("\n=== ANALYZING DUPLICATE INDONESIAN SPECIES ===")
    species_groups = defaultdict(list)
    for idx, row in fish_scraping.iterrows():
        species_groups[row['species_indonesia']].append({
            'index': idx,
            'nama_latin': row['nama_latin_normalized'],
            'row': row
        })
    
    duplicated_species = {k: v for k, v in species_groups.items() if len(v) > 1}
    print(f"Duplicated Indonesian species found: {len(duplicated_species)}")
    
    for species_name, entries in duplicated_species.items():
        print(f"\nSpecies '{species_name}' appears in:")
        for entry in entries:
            print(f"  - Row {entry['index']}: {entry['nama_latin']}")
    
    # Check which latin names from scraping exist in ikan_db
    print("\n=== MATCHING WITH IKAN_DB ===")
    scraping_latins = set()
    for nama_latin in fish_scraping['nama_latin_normalized'].dropna():
        if nama_latin:
            names = nama_latin.split(' ; ')
            for name in names:
                name = name.strip()
                if name:
                    scraping_latins.add(name)
    
    matching_names = scraping_latins & db_latin_names
    print(f"Latin names in scraping that match ikan_db: {len(matching_names)}")
    print(f"Latin names in scraping only: {len(scraping_latins - db_latin_names)}")
    print(f"Total unique latin names in scraping: {len(scraping_latins)}")
    
    return {
        'fish_scraping': fish_scraping,
        'ikan_db': ikan_db,
        'duplicated_latins': duplicated_latins,
        'duplicated_species': duplicated_species,
        'species_groups': species_groups
    }

if __name__ == "__main__":
    results = load_and_analyze()