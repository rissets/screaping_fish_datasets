#!/bin/bash

# Fish Image Scraper - Batch Runner
# Runs batch scraping in headless mode with customizable parameters

echo "🐟 Fish Image Scraper - Batch Mode 🐟"
echo "======================================"

# Function to display usage
usage() {
    echo "Usage: $0 [csv_file] [max_species] [priority] [output_dir]"
    echo ""
    echo "Parameters:"
    echo "  csv_file     - CSV database file (default: fish_scraping_list_updated.csv)"
    echo "  max_species  - Maximum number of species to process (default: 10)"
    echo "  priority     - Priority filter: HIGH/MEDIUM/LOW/ALL (default: HIGH)"
    echo "  output_dir   - Output directory (default: fish_images)"
    echo ""
    echo "Examples:"
    echo "  $0                                              # Use defaults"
    echo "  $0 fish_scraping_top50.csv                     # Use top 50 species"
    echo "  $0 fish_scraping_top50.csv 5                   # Process only 5 species"
    echo "  $0 fish_scraping_top50.csv 5 HIGH              # Process 5 HIGH priority species"
    echo "  $0 fish_scraping_top50.csv 5 HIGH my_images    # Custom output directory"
    exit 1
}

# Check for help flag
if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    usage
fi

# Set parameters with defaults
CSV_FILE=${1:-"fish_scraping_list_updated.csv"}
MAX_SPECIES=${2:-10}
PRIORITY=${3:-"HIGH"}
OUTPUT_DIR=${4:-"fish_images"}

# Validate parameters
if [ ! -f "$CSV_FILE" ]; then
    echo "❌ CSV file not found: $CSV_FILE"
    echo "Available CSV files:"
    ls -1 *.csv 2>/dev/null || echo "   No CSV files found"
    exit 1
fi

if ! [[ "$MAX_SPECIES" =~ ^[0-9]+$ ]] || [ "$MAX_SPECIES" -le 0 ]; then
    echo "❌ Invalid max_species: $MAX_SPECIES (must be a positive integer)"
    exit 1
fi

if [[ ! "$PRIORITY" =~ ^(HIGH|MEDIUM|LOW|ALL)$ ]]; then
    echo "❌ Invalid priority: $PRIORITY (must be HIGH, MEDIUM, LOW, or ALL)"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Please run setup_ubuntu.sh first"
    exit 1
fi

# Display configuration
echo "📋 Batch Scraping Configuration:"
echo "   📁 CSV Database: $CSV_FILE"
echo "   📊 Max Species: $MAX_SPECIES"
echo "   🏷️ Priority Filter: $PRIORITY"
echo "   📂 Output Directory: $OUTPUT_DIR"
echo ""

# Confirm execution
read -p "🚀 Start batch scraping? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Batch scraping cancelled"
    exit 0
fi

# Set environment for headless operation
export DISPLAY=:99
export CHROME_HEADLESS=1
export FIREFOX_HEADLESS=1

# Start Xvfb (virtual display)
echo "🖥️ Starting virtual display..."
Xvfb :99 -ac -screen 0 1280x1024x16 &
XVFB_PID=$!

# Wait for Xvfb to start
sleep 2

# Check if Xvfb started successfully
if ! ps -p $XVFB_PID > /dev/null; then
    echo "❌ Failed to start virtual display"
    exit 1
fi

echo "✅ Virtual display started (PID: $XVFB_PID)"

# Activate virtual environment
echo "🐍 Activating Python virtual environment..."
source venv/bin/activate

# Create directories
mkdir -p "$OUTPUT_DIR"
mkdir -p logs

# Generate log filename
LOG_FILE="logs/batch_$(date +%Y%m%d_%H%M%S).log"

echo "📝 Log file: $LOG_FILE"
echo "🚀 Starting batch scraping..."

# Create Python script for batch execution
BATCH_SCRIPT=$(cat << EOF
import sys
import os
sys.path.append('.')

from scraping import BatchFishScraper
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('$LOG_FILE'),
        logging.StreamHandler()
    ]
)

try:
    # Create batch scraper
    scraper = BatchFishScraper('$CSV_FILE', '$OUTPUT_DIR')
    
    # Set priority filter
    priority_filter = '$PRIORITY' if '$PRIORITY' != 'ALL' else None
    max_species = int('$MAX_SPECIES')
    
    print(f"🎯 Target: {max_species} species with priority {priority_filter or 'ALL'}")
    
    # Run batch scraping
    scraper.run_batch_scraping(
        max_species=max_species,
        priority_filter=priority_filter
    )
    
    print("✅ Batch scraping completed successfully!")
    
except Exception as e:
    print(f"❌ Batch scraping failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF
)

# Execute the batch script
echo "$BATCH_SCRIPT" | python3

# Capture exit code
SCRAPER_EXIT_CODE=$?

# Clean up
echo "🧹 Cleaning up virtual display..."
kill $XVFB_PID 2>/dev/null
sleep 1

# Show results
echo ""
echo "📊 BATCH SCRAPING SUMMARY"
echo "========================="
if [ $SCRAPER_EXIT_CODE -eq 0 ]; then
    echo "✅ Status: SUCCESS"
else
    echo "❌ Status: FAILED (exit code: $SCRAPER_EXIT_CODE)"
fi

# Count results
if [ -d "$OUTPUT_DIR" ]; then
    SPECIES_COUNT=$(find "$OUTPUT_DIR" -type d -mindepth 1 -maxdepth 1 | wc -l)
    TOTAL_IMAGES=$(find "$OUTPUT_DIR" -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" \) | wc -l)
    echo "📁 Species Processed: $SPECIES_COUNT"
    echo "📸 Total Images: $TOTAL_IMAGES"
    echo "📂 Output Directory: $OUTPUT_DIR"
else
    echo "📁 No output directory created"
fi

echo "📝 Log File: $LOG_FILE"
echo ""

# Show top 5 species by image count
if [ -d "$OUTPUT_DIR" ]; then
    echo "🏆 TOP 5 SPECIES BY IMAGE COUNT:"
    find "$OUTPUT_DIR" -type d -mindepth 1 -maxdepth 1 | while read species_dir; do
        species_name=$(basename "$species_dir")
        image_count=$(find "$species_dir" -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" \) | wc -l)
        echo "$image_count $species_name"
    done | sort -rn | head -5 | nl -w2 -s'. '
fi

echo ""
echo "🎉 Batch scraping completed!"

exit $SCRAPER_EXIT_CODE