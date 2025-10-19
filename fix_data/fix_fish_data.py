#!/usr/bin/env python3
"""
Script to fix and synchronize fish_scraping_list_updated.csv with ikan_db.csv
"""

import pandas as pd
import re
from collections import defaultdict

def fix_fish_scraping():
    # Load both files
    print("Loading files...")
    ikan_db = pd.read_csv('/Users/user/Dev/scraping_fish/ikan_db.csv')
    fish_scraping = pd.read_csv('/Users/user/Dev/scraping_fish/fish_scraping_list_updated.csv')
    
    print(f"Original fish_scraping: {len(fish_scraping)} rows")
    
    # Create mapping from ikan_db for reference
    db_mapping = {}
    for _, row in ikan_db.iterrows():
        if pd.notna(row['nama_latin']) and row['nama_latin'].strip():
            latin_name = str(row['nama_latin']).strip()
            db_mapping[latin_name] = {
                'nama_umum': row.get('nama_umum', ''),
                'nama_inggris': row.get('nama_inggris', ''),
                'nama_daerah': row.get('nama_daerah', ''),
                'kelompok_indonesia': row.get('kelompok_indonesia', ''),
                'jenis_perairan': row.get('jenis_perairan', ''),
                'jenis_konsumsi': row.get('jenis_konsumsi', ''),
                'jenis_hias': row.get('jenis_hias', ''),
                'jenis_dilindungi': row.get('jenis_dilindungi', '')
            }
    
    # Standardize field mappings
    field_mapping = {
        'species_indonesia': 'nama_umum',  # Use nama_umum from ikan_db as reference
        'species_english': 'nama_inggris',
        'kelompok': 'kelompok_indonesia'
    }
    
    # Check and update fish_scraping based on ikan_db
    updated_rows = []
    issues_found = []
    
    for idx, row in fish_scraping.iterrows():
        updated_row = row.copy()
        
        # Extract first latin name for lookup
        latin_names = str(row['nama_latin']).split(' ; ') if pd.notna(row['nama_latin']) else ['']
        primary_latin = latin_names[0].strip() if latin_names[0] else ''
        
        if primary_latin and primary_latin in db_mapping:
            db_info = db_mapping[primary_latin]
            
            # Check consistency with ikan_db
            checks = []
            
            # Check species_indonesia vs nama_umum
            if pd.notna(db_info['nama_umum']) and db_info['nama_umum'].strip():
                db_species = str(db_info['nama_umum']).strip().lower()
                scraping_species = str(row['species_indonesia']).strip().lower()
                if db_species != scraping_species:
                    checks.append(f"Species mismatch: scraping='{scraping_species}' vs db='{db_species}'")
            
            # Check jenis_perairan
            if pd.notna(db_info['jenis_perairan']) and db_info['jenis_perairan'].strip():
                db_perairan = str(db_info['jenis_perairan']).strip().upper()
                scraping_perairan = str(row['jenis_perairan']).strip().upper()
                if db_perairan != scraping_perairan:
                    checks.append(f"Jenis_perairan mismatch: scraping='{scraping_perairan}' vs db='{db_perairan}'")
            
            # Check jenis_konsumsi  
            if pd.notna(db_info['jenis_konsumsi']) and db_info['jenis_konsumsi'].strip():
                db_konsumsi = str(db_info['jenis_konsumsi']).strip().upper()
                scraping_konsumsi = str(row['jenis_konsumsi']).strip().upper()
                if db_konsumsi != scraping_konsumsi:
                    checks.append(f"Jenis_konsumsi mismatch: scraping='{scraping_konsumsi}' vs db='{db_konsumsi}'")
            
            if checks:
                issues_found.append({
                    'row': idx + 2,  # +2 for header and 0-indexing
                    'latin_name': primary_latin,
                    'species': row['species_indonesia'],
                    'issues': checks
                })
        
        updated_rows.append(updated_row)
    
    # Report issues
    print(f"\n=== CONSISTENCY ISSUES FOUND ===")
    print(f"Total issues: {len(issues_found)}")
    
    for issue in issues_found[:10]:  # Show first 10 issues
        print(f"\nRow {issue['row']}: {issue['species']} ({issue['latin_name']})")
        for check in issue['issues']:
            print(f"  - {check}")
    
    if len(issues_found) > 10:
        print(f"  ... and {len(issues_found) - 10} more issues")
    
    # Look for exact duplicates in the entire dataset
    print(f"\n=== CHECKING FOR EXACT DUPLICATES ===")
    
    # Check for duplicate rows (ignoring index)
    duplicate_rows = fish_scraping[fish_scraping.duplicated(keep=False)]
    if len(duplicate_rows) > 0:
        print(f"Found {len(duplicate_rows)} duplicate rows")
        print(duplicate_rows[['species_indonesia', 'nama_latin']].head())
    else:
        print("No exact duplicate rows found")
    
    # Check for duplicate latin names (considering multiple names per row)
    latin_name_occurrences = defaultdict(list)
    for idx, row in fish_scraping.iterrows():
        if pd.notna(row['nama_latin']):
            latin_names = str(row['nama_latin']).split(' ; ')
            for latin_name in latin_names:
                latin_name = latin_name.strip()
                if latin_name:
                    latin_name_occurrences[latin_name].append({
                        'row': idx + 2,
                        'species': row['species_indonesia'],
                        'full_latin': row['nama_latin']
                    })
    
    duplicate_latins = {k: v for k, v in latin_name_occurrences.items() if len(v) > 1}
    print(f"\nDuplicate latin names: {len(duplicate_latins)}")
    
    for latin_name, occurrences in list(duplicate_latins.items())[:5]:  # Show first 5
        print(f"\n'{latin_name}' appears in:")
        for occ in occurrences:
            print(f"  Row {occ['row']}: {occ['species']}")
    
    # Check for duplicate species_indonesia
    species_occurrences = defaultdict(list)
    for idx, row in fish_scraping.iterrows():
        species_name = str(row['species_indonesia']).strip()
        species_occurrences[species_name].append({
            'row': idx + 2,
            'latin': row['nama_latin']
        })
    
    duplicate_species = {k: v for k, v in species_occurrences.items() if len(v) > 1}
    print(f"\nDuplicate species_indonesia: {len(duplicate_species)}")
    
    for species_name, occurrences in list(duplicate_species.items())[:5]:  # Show first 5
        print(f"\n'{species_name}' appears in:")
        for occ in occurrences:
            print(f"  Row {occ['row']}: {occ['latin']}")
    
    # If duplicates found, create cleaned version
    if duplicate_latins or duplicate_species:
        print(f"\n=== CREATING CLEANED VERSION ===")
        cleaned_data = clean_duplicates(fish_scraping, duplicate_latins, duplicate_species)
        return cleaned_data
    else:
        print(f"\n=== NO DUPLICATES FOUND - FILE IS CLEAN ===")
        return fish_scraping

def clean_duplicates(df, duplicate_latins, duplicate_species):
    """Clean duplicates by merging entries with same species_indonesia"""
    
    print("Cleaning duplicates...")
    
    # Group by species_indonesia
    species_groups = df.groupby('species_indonesia')
    cleaned_rows = []
    
    for species_name, group in species_groups:
        if len(group) == 1:
            # No duplicates, keep as is
            cleaned_rows.append(group.iloc[0])
        else:
            # Multiple entries with same species_indonesia - merge them
            print(f"Merging {len(group)} entries for species: {species_name}")
            
            merged_row = group.iloc[0].copy()  # Start with first row
            
            # Merge nama_latin fields
            all_latin_names = []
            for _, row in group.iterrows():
                if pd.notna(row['nama_latin']):
                    latin_names = str(row['nama_latin']).split(' ; ')
                    for name in latin_names:
                        name = name.strip()
                        if name and name not in all_latin_names:
                            all_latin_names.append(name)
            
            merged_row['nama_latin'] = ' ; '.join(all_latin_names)
            
            # Merge nama_daerah
            all_daerah = []
            for _, row in group.iterrows():
                if pd.notna(row['nama_daerah']) and str(row['nama_daerah']).strip():
                    daerah_names = str(row['nama_daerah']).split(';')
                    for name in daerah_names:
                        name = name.strip()
                        if name and name not in all_daerah:
                            all_daerah.append(name)
            
            if all_daerah:
                merged_row['nama_daerah'] = '; '.join(all_daerah)
            
            # For other fields, take the most common value or first non-null
            for col in ['species_english', 'kelompok', 'jenis_perairan', 'jenis_konsumsi', 'jenis_hias', 'jenis_dilindungi']:
                values = [str(row[col]).strip() for _, row in group.iterrows() 
                         if pd.notna(row[col]) and str(row[col]).strip()]
                if values:
                    # Use most common value
                    from collections import Counter
                    most_common = Counter(values).most_common(1)[0][0]
                    merged_row[col] = most_common
            
            cleaned_rows.append(merged_row)
    
    cleaned_df = pd.DataFrame(cleaned_rows)
    print(f"Cleaned data: {len(cleaned_df)} rows (reduced from {len(df)})")
    
    return cleaned_df

if __name__ == "__main__":
    result = fix_fish_scraping()
    
    # Save the result
    output_file = '/Users/user/Dev/scraping_fish/fish_scraping_list_fixed.csv'
    result.to_csv(output_file, index=False)
    print(f"\nFixed data saved to: {output_file}")
    print(f"Final row count: {len(result)}")