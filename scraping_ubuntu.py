#!/usr/bin/env python3
"""
Fish Image Scraper - Ubuntu Server Optimized Version
Includes headless operation and server-specific optimizations
"""

import os
import sys
import logging
from scraping import FishImageScraper, BatchFishScraper

# Configure logging for server environment
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def setup_headless_display():
    """Setup virtual display for headless operation"""
    try:
        from pyvirtualdisplay import Display
        display = Display(visible=0, size=(1280, 1024))
        display.start()
        logger.info("✅ Virtual display started for headless operation")
        return display
    except ImportError:
        logger.warning("pyvirtualdisplay not available, trying XVFB")
        os.environ['DISPLAY'] = ':99'
        return None
    except Exception as e:
        logger.error(f"Failed to start virtual display: {e}")
        return None

def optimize_for_server():
    """Apply server-specific optimizations"""
    
    # Set environment variables for headless operation
    os.environ.setdefault('DISPLAY', ':99')
    os.environ.setdefault('CHROME_HEADLESS', '1')
    os.environ.setdefault('FIREFOX_HEADLESS', '1')
    
    # Reduce memory usage
    import gc
    gc.set_threshold(100, 10, 10)
    
    # Set conservative limits
    os.environ.setdefault('MAX_CONCURRENT_DOWNLOADS', '2')
    os.environ.setdefault('DOWNLOAD_DELAY', '2')
    
    logger.info("✅ Server optimizations applied")

def run_single_species_headless():
    """Run single species scraping in headless mode"""
    print("🐟 Fish Image Scraper - Ubuntu Server Mode 🐟")
    print("=" * 50)
    
    # Get input
    species = input("Enter fish species name: ").strip()
    if not species:
        print("❌ Species name cannot be empty!")
        return
    
    scientific_name = input("Enter scientific name (optional): ").strip()
    if not scientific_name:
        scientific_name = None
    
    try:
        min_images = int(input("Minimum number of images: ").strip())
        if min_images <= 0:
            print("❌ Number of images must be greater than 0!")
            return
    except ValueError:
        print("❌ Please enter a valid number!")
        return
    
    output_dir = input("Output directory (default: fish_images): ").strip()
    if not output_dir:
        output_dir = "fish_images"
    
    # Setup headless display
    display = setup_headless_display()
    
    try:
        # Run scraping
        scraper = FishImageScraper(species, min_images, output_dir, scientific_name)
        downloaded = scraper.run_scraping()
        
        print(f"\n{'='*50}")
        if downloaded >= min_images:
            print(f"✅ SUCCESS! Downloaded {downloaded} images")
        else:
            print(f"⚠️ PARTIAL SUCCESS! Downloaded {downloaded}/{min_images} images")
        
        print(f"📁 Images saved in: {scraper.species_dir}")
        print(f"{'='*50}")
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        print(f"❌ Scraping failed: {e}")
    finally:
        if display:
            display.stop()

def run_batch_headless():
    """Run batch scraping in headless mode"""
    print("🐟 Fish Batch Scraper - Ubuntu Server Mode 🐟")
    print("=" * 50)
    
    # Check available CSV files
    csv_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'fish' in f]
    if not csv_files:
        print("❌ No fish CSV files found!")
        return
    
    print("Available CSV files:")
    for i, csv_file in enumerate(csv_files, 1):
        print(f"{i}. {csv_file}")
    
    try:
        choice = int(input("Select CSV file (number): ").strip())
        if choice < 1 or choice > len(csv_files):
            print("❌ Invalid choice!")
            return
        csv_file = csv_files[choice - 1]
    except ValueError:
        print("❌ Please enter a valid number!")
        return
    
    # Get parameters
    priorities = ['HIGH', 'MEDIUM', 'LOW', 'ALL']
    print("Priority levels:", ", ".join(priorities))
    priority = input("Priority filter (HIGH/MEDIUM/LOW/ALL): ").strip().upper()
    if priority not in priorities:
        priority = 'ALL'
    
    max_species = input("Max species (empty for all): ").strip()
    max_species = int(max_species) if max_species.isdigit() else None
    
    output_dir = input("Output directory (default: fish_images): ").strip()
    if not output_dir:
        output_dir = "fish_images"
    
    print(f"\n🎯 BATCH SCRAPING SETUP:")
    print(f"📁 Database: {csv_file}")
    print(f"🏷️ Priority: {priority}")
    print(f"📊 Max species: {max_species or 'ALL'}")
    print(f"📂 Output: {output_dir}")
    
    confirm = input("\nStart batch scraping? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Batch scraping cancelled")
        return
    
    # Setup headless display
    display = setup_headless_display()
    
    try:
        # Run batch scraping
        batch_scraper = BatchFishScraper(csv_file, output_dir)
        priority_filter = priority if priority != 'ALL' else None
        
        batch_scraper.run_batch_scraping(
            max_species=max_species,
            priority_filter=priority_filter
        )
        
    except Exception as e:
        logger.error(f"Batch scraping failed: {e}")
        print(f"❌ Batch scraping failed: {e}")
    finally:
        if display:
            display.stop()

def main():
    """Main function for Ubuntu server mode"""
    
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    # Apply server optimizations
    optimize_for_server()
    
    print("🐟 Fish Image Scraper - Ubuntu Server Edition 🐟")
    print("=" * 55)
    print("Optimized for headless server operation")
    print("=" * 55)
    
    # Check if running in headless environment
    if 'DISPLAY' not in os.environ or os.environ.get('SSH_CONNECTION'):
        logger.info("Detected headless/SSH environment")
    
    # Mode selection
    print("\nSelect scraping mode:")
    print("1. Single Species")
    print("2. Batch Scraping (from CSV)")
    print("3. Test Mode (minimal scraping)")
    
    while True:
        mode = input("Choice (1-3): ").strip()
        if mode in ['1', '2', '3']:
            break
        print("❌ Invalid choice!")
    
    try:
        if mode == '1':
            run_single_species_headless()
        elif mode == '2':
            run_batch_headless()
        elif mode == '3':
            # Test mode - single species with minimal images
            print("\n🧪 Test Mode - Quick validation")
            display = setup_headless_display()
            try:
                scraper = FishImageScraper("goldfish", 3, "test_images", "Carassius auratus")
                downloaded = scraper.run_scraping()
                print(f"✅ Test completed: {downloaded} images downloaded")
            finally:
                if display:
                    display.stop()
    
    except KeyboardInterrupt:
        print("\n❌ Operation interrupted by user")
        logger.info("Operation interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()