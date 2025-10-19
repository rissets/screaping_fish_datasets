#!/usr/bin/env python3
"""
Script to synchronize fish_scraping_list_updated.csv with ikan_db.csv
Use ikan_db.csv as the authoritative source for species names and properties
"""

import pandas as pd
import re
from collections import defaultdict

def synchronize_with_ikan_db():
    # Load both files
    print("Loading files...")
    ikan_db = pd.read_csv('/Users/user/Dev/scraping_fish/ikan_db.csv')
    fish_scraping = pd.read_csv('/Users/user/Dev/scraping_fish/fish_scraping_list_updated.csv')
    
    print(f"ikan_db: {len(ikan_db)} rows")
    print(f"fish_scraping original: {len(fish_scraping)} rows")
    
    # Create mapping from ikan_db using nama_latin as key
    db_mapping = {}
    latin_to_db_row = {}
    
    for _, row in ikan_db.iterrows():
        if pd.notna(row['nama_latin']) and str(row['nama_latin']).strip():
            latin_name = str(row['nama_latin']).strip()
            db_mapping[latin_name] = row
            latin_to_db_row[latin_name] = row
    
    print(f"Created mapping for {len(db_mapping)} latin names from ikan_db")
    
    # Process fish_scraping and synchronize with ikan_db
    synchronized_rows = []
    unmatched_entries = []
    updates_made = 0
    
    for idx, scraping_row in fish_scraping.iterrows():
        # Get the first latin name from scraping data
        latin_names_str = str(scraping_row['nama_latin']) if pd.notna(scraping_row['nama_latin']) else ''
        latin_names = [name.strip() for name in latin_names_str.split(' ; ') if name.strip()]
        
        primary_latin = latin_names[0] if latin_names else ''
        
        if primary_latin and primary_latin in db_mapping:
            # Found match in ikan_db - synchronize the data
            db_row = db_mapping[primary_latin]
            
            # Create synchronized row starting with scraping data structure
            sync_row = scraping_row.copy()
            
            # Update with authoritative data from ikan_db
            updates_in_row = []
            
            # Update species_indonesia with nama_umum from ikan_db
            if pd.notna(db_row['nama_umum']) and str(db_row['nama_umum']).strip():
                old_species = str(sync_row['species_indonesia'])
                new_species = str(db_row['nama_umum']).strip()
                if old_species.lower() != new_species.lower():
                    sync_row['species_indonesia'] = new_species
                    updates_in_row.append(f"species_indonesia: '{old_species}' → '{new_species}'")
            
            # Update species_english with nama_inggris from ikan_db
            if pd.notna(db_row['nama_inggris']) and str(db_row['nama_inggris']).strip():
                old_english = str(sync_row['species_english'])
                new_english = str(db_row['nama_inggris']).strip()
                if old_english.lower() != new_english.lower():
                    sync_row['species_english'] = new_english
                    updates_in_row.append(f"species_english: '{old_english}' → '{new_english}'")
            
            # Update kelompok with kelompok_indonesia from ikan_db  
            if pd.notna(db_row['kelompok_indonesia']) and str(db_row['kelompok_indonesia']).strip():
                old_kelompok = str(sync_row['kelompok'])
                new_kelompok = str(db_row['kelompok_indonesia']).strip()
                if old_kelompok.lower() != new_kelompok.lower():
                    sync_row['kelompok'] = new_kelompok
                    updates_in_row.append(f"kelompok: '{old_kelompok}' → '{new_kelompok}'")
            
            # Update jenis_perairan
            if pd.notna(db_row['jenis_perairan']) and str(db_row['jenis_perairan']).strip():
                old_perairan = str(sync_row['jenis_perairan'])
                new_perairan = str(db_row['jenis_perairan']).strip().upper()
                if old_perairan.upper() != new_perairan:
                    sync_row['jenis_perairan'] = new_perairan
                    updates_in_row.append(f"jenis_perairan: '{old_perairan}' → '{new_perairan}'")
            
            # Update jenis_konsumsi
            if pd.notna(db_row['jenis_konsumsi']) and str(db_row['jenis_konsumsi']).strip():
                old_konsumsi = str(sync_row['jenis_konsumsi'])
                new_konsumsi = str(db_row['jenis_konsumsi']).strip().upper()
                if old_konsumsi.upper() != new_konsumsi:
                    sync_row['jenis_konsumsi'] = new_konsumsi
                    updates_in_row.append(f"jenis_konsumsi: '{old_konsumsi}' → '{new_konsumsi}'")
            
            # Update jenis_hias 
            if pd.notna(db_row['jenis_hias']) and str(db_row['jenis_hias']).strip():
                old_hias = str(sync_row['jenis_hias'])
                new_hias = str(db_row['jenis_hias']).strip().upper()
                if old_hias.upper() != new_hias:
                    sync_row['jenis_hias'] = new_hias
                    updates_in_row.append(f"jenis_hias: '{old_hias}' → '{new_hias}'")
            
            # Update jenis_dilindungi
            if pd.notna(db_row['jenis_dilindungi']) and str(db_row['jenis_dilindungi']).strip():
                old_dilindungi = str(sync_row['jenis_dilindungi'])
                new_dilindungi = str(db_row['jenis_dilindungi']).strip().upper()
                if old_dilindungi.upper() != new_dilindungi:
                    sync_row['jenis_dilindungi'] = new_dilindungi
                    updates_in_row.append(f"jenis_dilindungi: '{old_dilindungi}' → '{new_dilindungi}'")
            
            # Update nama_daerah if available in ikan_db
            if pd.notna(db_row['nama_daerah']) and str(db_row['nama_daerah']).strip():
                db_nama_daerah = str(db_row['nama_daerah']).strip()
                scraping_nama_daerah = str(sync_row['nama_daerah']).strip()
                
                # Merge both if they're different but both have content
                if db_nama_daerah and scraping_nama_daerah and db_nama_daerah.lower() != scraping_nama_daerah.lower():
                    # Combine unique entries
                    all_daerah = set()
                    for daerah_str in [db_nama_daerah, scraping_nama_daerah]:
                        daerah_parts = [d.strip() for d in daerah_str.split(';') if d.strip()]
                        all_daerah.update(daerah_parts)
                    merged_daerah = '; '.join(sorted(all_daerah))
                    sync_row['nama_daerah'] = merged_daerah
                    updates_in_row.append(f"nama_daerah: merged with ikan_db")
                elif db_nama_daerah and not scraping_nama_daerah:
                    sync_row['nama_daerah'] = db_nama_daerah
                    updates_in_row.append(f"nama_daerah: added from ikan_db")
            
            if updates_in_row:
                updates_made += 1
                if updates_made <= 10:  # Show first 10 updates
                    print(f"\nRow {idx + 2}: {sync_row['species_indonesia']} ({primary_latin})")
                    for update in updates_in_row:
                        print(f"  - {update}")
            
            synchronized_rows.append(sync_row)
        else:
            # No match found in ikan_db
            unmatched_entries.append({
                'row': idx + 2,
                'species': scraping_row['species_indonesia'],
                'latin_name': primary_latin
            })
            # Keep original data for unmatched entries
            synchronized_rows.append(scraping_row)
    
    print(f"\n=== SYNCHRONIZATION SUMMARY ===")
    print(f"Total updates made: {updates_made}")
    print(f"Unmatched entries: {len(unmatched_entries)}")
    
    if unmatched_entries and len(unmatched_entries) <= 20:
        print(f"\nUnmatched entries:")
        for entry in unmatched_entries:
            print(f"  Row {entry['row']}: {entry['species']} ({entry['latin_name']})")
    elif unmatched_entries:
        print(f"\nFirst 20 unmatched entries:")
        for entry in unmatched_entries[:20]:
            print(f"  Row {entry['row']}: {entry['species']} ({entry['latin_name']})")
        print(f"  ... and {len(unmatched_entries) - 20} more")
    
    # Create DataFrame from synchronized data
    synchronized_df = pd.DataFrame(synchronized_rows)
    
    # Remove any exact duplicates that might have been created
    original_count = len(synchronized_df)
    synchronized_df = synchronized_df.drop_duplicates()
    final_count = len(synchronized_df)
    
    if original_count != final_count:
        print(f"Removed {original_count - final_count} duplicate rows")
    
    return synchronized_df, len(unmatched_entries), updates_made

if __name__ == "__main__":
    result_df, unmatched_count, update_count = synchronize_with_ikan_db()
    
    # Save the synchronized data
    output_file = '/Users/user/Dev/scraping_fish/fish_scraping_list_synchronized.csv'
    result_df.to_csv(output_file, index=False)
    
    print(f"\n=== FINAL RESULT ===")
    print(f"Synchronized data saved to: {output_file}")
    print(f"Final row count: {len(result_df)}")
    print(f"Records updated: {update_count}")
    print(f"Records unmatched with ikan_db: {unmatched_count}")
    
    if unmatched_count == 0 and update_count > 0:
        print("\n✅ SUCCESS: All records synchronized with ikan_db!")
    elif unmatched_count == 0:
        print("\n✅ SUCCESS: All records already consistent with ikan_db!")
    else:
        print(f"\n⚠️  WARNING: {unmatched_count} records could not be matched with ikan_db")