#!/usr/bin/env python3
"""
Final cleanup script to remove latin name duplicates and merge entries with same species
"""

import pandas as pd
from collections import defaultdict, Counter

def final_cleanup():
    # Load synchronized data
    print("Loading synchronized data...")
    df = pd.read_csv('/Users/user/Dev/scraping_fish/fish_scraping_list_synchronized.csv')
    print(f"Original data: {len(df)} rows")
    
    # Analyze latin name duplicates across all entries
    print("\n=== ANALYZING LATIN NAME DUPLICATES ===")
    
    # Create mapping of individual latin names to rows
    latin_to_rows = defaultdict(list)
    
    for idx, row in df.iterrows():
        if pd.notna(row['nama_latin']) and str(row['nama_latin']).strip():
            # Split multiple latin names  
            latin_names = str(row['nama_latin']).split(' ; ')
            for latin_name in latin_names:
                latin_name = latin_name.strip()
                if latin_name:
                    latin_to_rows[latin_name].append({
                        'index': idx,
                        'species_indonesia': row['species_indonesia'],
                        'row_data': row
                    })
    
    # Find duplicated latin names
    duplicated_latins = {k: v for k, v in latin_to_rows.items() if len(v) > 1}
    print(f"Latin names that appear in multiple rows: {len(duplicated_latins)}")
    
    if duplicated_latins:
        print("\nDuplicated latin names:")
        for latin_name, entries in list(duplicated_latins.items())[:10]:
            print(f"\n'{latin_name}' appears in {len(entries)} rows:")
            for entry in entries:
                print(f"  - Row {entry['index'] + 1}: {entry['species_indonesia']}")
    
    # Group by species_indonesia for potential merging
    print(f"\n=== ANALYZING SPECIES DUPLICATES ===")
    species_groups = df.groupby('species_indonesia')
    duplicate_species = []
    
    for species_name, group in species_groups:
        if len(group) > 1:
            duplicate_species.append({
                'species': species_name, 
                'count': len(group),
                'rows': group.index.tolist(),
                'data': group
            })
    
    print(f"Species that appear in multiple rows: {len(duplicate_species)}")
    
    if duplicate_species:
        print("\nDuplicate species:")
        for dup in duplicate_species[:10]:
            print(f"  '{dup['species']}': {dup['count']} rows")
    
    # Create cleaned dataset
    print(f"\n=== CREATING CLEANED DATASET ===")
    
    if not duplicate_species and not duplicated_latins:
        print("No duplicates found - dataset is already clean!")
        return df
    
    # Process each species group
    cleaned_rows = []
    merge_log = []
    
    for species_name, group in species_groups:
        if len(group) == 1:
            # Single entry - keep as is
            cleaned_rows.append(group.iloc[0])
        else:
            # Multiple entries - merge them
            print(f"Merging {len(group)} entries for species: {species_name}")
            
            # Start with the first row
            merged_row = group.iloc[0].copy()
            
            # Collect all unique latin names
            all_latin_names = set()
            for _, row in group.iterrows():
                if pd.notna(row['nama_latin']):
                    latin_names = str(row['nama_latin']).split(' ; ')
                    for name in latin_names:
                        name = name.strip()
                        if name:
                            all_latin_names.add(name)
            
            merged_row['nama_latin'] = ' ; '.join(sorted(all_latin_names))
            
            # Merge nama_daerah
            all_daerah = set()
            for _, row in group.iterrows():
                if pd.notna(row['nama_daerah']) and str(row['nama_daerah']).strip():
                    daerah_names = str(row['nama_daerah']).split(';')
                    for name in daerah_names:
                        name = name.strip()
                        if name:
                            all_daerah.add(name)
            
            if all_daerah:
                merged_row['nama_daerah'] = '; '.join(sorted(all_daerah))
            
            # Merge search_keywords
            all_keywords = set()
            for _, row in group.iterrows():
                if pd.notna(row['search_keywords']) and str(row['search_keywords']).strip():
                    keywords = str(row['search_keywords']).split(' ; ')
                    for kw in keywords:
                        kw = kw.strip()
                        if kw:
                            all_keywords.add(kw)
            
            if all_keywords:
                merged_row['search_keywords'] = ' ; '.join(sorted(all_keywords))
            
            # For other fields, use most common value or first non-null
            for col in ['species_english', 'kelompok', 'jenis_perairan', 'jenis_konsumsi', 'jenis_hias', 'jenis_dilindungi', 'prioritas']:
                values = []
                for _, row in group.iterrows():
                    if pd.notna(row[col]) and str(row[col]).strip():
                        values.append(str(row[col]).strip())
                
                if values:
                    # Use most common value
                    most_common = Counter(values).most_common(1)[0][0]
                    merged_row[col] = most_common
            
            # Use maximum min_images
            min_images_values = [row['min_images'] for _, row in group.iterrows() 
                               if pd.notna(row['min_images'])]
            if min_images_values:
                merged_row['min_images'] = max(min_images_values)
            
            merge_log.append({
                'species': species_name,
                'original_count': len(group),
                'merged_latin_names': len(all_latin_names)
            })
            
            cleaned_rows.append(merged_row)
    
    # Create final dataframe
    cleaned_df = pd.DataFrame(cleaned_rows)
    
    print(f"\n=== CLEANUP SUMMARY ===")
    print(f"Original rows: {len(df)}")
    print(f"Cleaned rows: {len(cleaned_df)}")
    print(f"Rows removed by merging: {len(df) - len(cleaned_df)}")
    print(f"Species groups merged: {len(merge_log)}")
    
    if merge_log:
        print(f"\nMerge details:")
        for log in merge_log[:10]:
            print(f"  {log['species']}: {log['original_count']} rows → 1 row ({log['merged_latin_names']} latin names)")
    
    # Final duplicate check
    print(f"\n=== FINAL DUPLICATE CHECK ===")
    
    # Check for remaining species duplicates
    final_species_counts = cleaned_df['species_indonesia'].value_counts()
    remaining_duplicates = final_species_counts[final_species_counts > 1]
    
    if len(remaining_duplicates) > 0:
        print(f"WARNING: {len(remaining_duplicates)} species still have duplicates:")
        for species, count in remaining_duplicates.head().items():
            print(f"  {species}: {count} entries")
    else:
        print("✅ No species duplicates remain")
    
    # Check for remaining latin name duplicates
    final_latin_to_rows = defaultdict(list)
    for idx, row in cleaned_df.iterrows():
        if pd.notna(row['nama_latin']):
            latin_names = str(row['nama_latin']).split(' ; ')
            for latin_name in latin_names:
                latin_name = latin_name.strip()
                if latin_name:
                    final_latin_to_rows[latin_name].append(row['species_indonesia'])
    
    final_duplicated_latins = {k: v for k, v in final_latin_to_rows.items() if len(v) > 1}
    
    if final_duplicated_latins:
        print(f"WARNING: {len(final_duplicated_latins)} latin names still appear in multiple entries:")
        for latin_name, species_list in list(final_duplicated_latins.items())[:5]:
            print(f"  '{latin_name}': {species_list}")
    else:
        print("✅ No latin name duplicates remain")
    
    return cleaned_df

if __name__ == "__main__":
    result = final_cleanup()
    
    # Save final cleaned data
    output_file = '/Users/user/Dev/scraping_fish/fish_scraping_list_final.csv'
    result.to_csv(output_file, index=False)
    
    print(f"\n=== FINAL OUTPUT ===")
    print(f"Final cleaned data saved to: {output_file}")
    print(f"Final row count: {len(result)}")
    print(f"Dataset is ready for use!")