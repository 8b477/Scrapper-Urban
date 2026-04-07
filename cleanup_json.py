import sys
import os
import json
from pathlib import Path

# Ajouter le répertoire "site de la ville" au path pour importer le module common
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "site de la ville"))

from common.utils import clean_description, format_iso_to_short


def process_json_file(filepath):
    """Process a single JSON file"""
    print(f"\nProcessing: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Process events
    if 'events' in data:
        for event in data['events']:
            # Clean description
            if 'description' in event and event['description']:
                event['description'] = clean_description(event['description'])
            
            # Transform dates
            if 'dates' in event:
                dates = event['dates']
                if 'start' in dates and dates['start']:
                    dates['start'] = format_iso_to_short(dates['start'])
                if 'end' in dates and dates['end']:
                    dates['end'] = format_iso_to_short(dates['end'])
    
    # Save modified file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Saved: {filepath}")

# Process all 5 cities
cities = [
    r"c:\Users\jonat\OneDrive\Bureau\Scrapper-Urban\site de la ville\Charleroi\charleroi_03-04-26.json",
    r"c:\Users\jonat\OneDrive\Bureau\Scrapper-Urban\site de la ville\La Louvière\lalouviere_03-04-26.json",
    r"c:\Users\jonat\OneDrive\Bureau\Scrapper-Urban\site de la ville\Liège\liege_03-04-26.json",
    r"c:\Users\jonat\OneDrive\Bureau\Scrapper-Urban\site de la ville\Mons\mons_03-04-26.json",
    r"c:\Users\jonat\OneDrive\Bureau\Scrapper-Urban\site de la ville\Namur\namur_03-04-26.json",
]

print("=" * 60)
print("CLEANING JSON FILES")
print("=" * 60)

for city_file in cities:
    if Path(city_file).exists():
        process_json_file(city_file)
    else:
        print(f"✗ File not found: {city_file}")

print("\n" + "=" * 60)
print("CLEANUP COMPLETE")
print("=" * 60)
