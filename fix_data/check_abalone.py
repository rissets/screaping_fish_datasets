#!/usr/bin/env python3
"""
Check abalone data in ikan_db.csv
"""

import pandas as pd

# Load ikan_db
ikan_db = pd.read_csv('/Users/user/Dev/scraping_fish/ikan_db.csv')

# Filter for abalone entries
abalone_entries = ikan_db[
    (ikan_db['nama_latin'].str.contains('Haliotis', na=False, case=False)) |
    (ikan_db['nama_latin'].str.contains('Vivere haliotis', na=False, case=False)) |
    (ikan_db['nama_umum'].str.contains('abalone', na=False, case=False))
]

print("=== ABALONE ENTRIES IN IKAN_DB.CSV ===")
print(f"Total abalone entries found: {len(abalone_entries)}")
print()

# Display key fields
for idx, row in abalone_entries.iterrows():
    print(f"Entry {idx + 1}:")
    print(f"  ID: {row['id']}")
    print(f"  Nama Latin: {row['nama_latin']}")
    print(f"  Nama Umum: {row['nama_umum']}")
    print(f"  Nama Inggris: {row['nama_inggris']}")
    print(f"  Kelompok Indonesia: {row['kelompok_indonesia']}")
    print(f"  Jenis Perairan: {row['jenis_perairan']}")
    print(f"  Jenis Konsumsi: {row['jenis_konsumsi']}")
    print(f"  Jenis Hias: {row['jenis_hias']}")
    print(f"  Jenis Dilindungi: {row['jenis_dilindungi']}")
    print()

# Check which one matches our scraping data first entry
print("=== COMPARISON WITH SCRAPING DATA ===")
scraping_df = pd.read_csv('/Users/user/Dev/scraping_fish/fish_scraping_list_updated.csv')
abalone_scraping = scraping_df[scraping_df['species_indonesia'].str.contains('Abalone', na=False, case=False)]

if len(abalone_scraping) > 0:
    print("Abalone entry in scraping data:")
    abalone_row = abalone_scraping.iloc[0]
    print(f"  Species Indonesia: {abalone_row['species_indonesia']}")
    print(f"  Species English: {abalone_row['species_english']}")
    print(f"  Nama Latin: {abalone_row['nama_latin']}")
    print(f"  Kelompok: {abalone_row['kelompok']}")
    print(f"  Jenis Perairan: {abalone_row['jenis_perairan']}")
    print()
    
    # Check which ikan_db entry was used
    primary_latin = abalone_row['nama_latin'].split(' ; ')[0].strip()
    matching_db = ikan_db[ikan_db['nama_latin'] == primary_latin]
    
    if len(matching_db) > 0:
        print(f"Matching ikan_db entry for '{primary_latin}':")
        match_row = matching_db.iloc[0]
        print(f"  Nama Umum: {match_row['nama_umum']}")
        print(f"  Nama Inggris: {match_row['nama_inggris']}")
        print(f"  Kelompok Indonesia: {match_row['kelompok_indonesia']}")
        print(f"  Jenis Perairan: {match_row['jenis_perairan']}")
else:
    print("No abalone entry found in scraping data")