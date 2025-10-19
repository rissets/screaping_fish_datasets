#!/usr/bin/env python3
"""
Fish Image Scraper - Ubuntu Server Optimized Version
Includes headless operation, server-specific optimizations, and enhanced Google Images scraping
"""

import os
import sys
import logging
import argparse
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
    """Run batch scraping in headless mode with enhanced options"""
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
    
    # Get parameters with enhanced options
    priorities = ['HIGH', 'MEDIUM', 'LOW', 'ALL']
    print("Priority levels:", ", ".join(priorities))
    priority = input("Priority filter (HIGH/MEDIUM/LOW/ALL): ").strip().upper()
    if priority not in priorities:
        priority = 'ALL'
    
    max_species = input("Max species (empty for all): ").strip()
    max_species = int(max_species) if max_species.isdigit() else None
    
    # Add start row option
    start_row = input("Start from row number (0 for beginning): ").strip()
    start_row = int(start_row) if start_row.isdigit() else 0
    
    # Add images per species option
    images_per_species = input("Target images per species (default 10): ").strip()
    images_per_species = int(images_per_species) if images_per_species.isdigit() else 10
    
    output_dir = input("Output directory (default: fish_images): ").strip()
    if not output_dir:
        output_dir = "fish_images"
    
    print(f"\n🎯 BATCH SCRAPING SETUP:")
    print(f"📁 Database: {csv_file}")
    print(f"📍 Start Row: {start_row}")
    print(f"🏷️ Priority: {priority}")
    print(f"📊 Max species: {max_species or 'ALL'}")
    print(f"🎯 Images per species: {images_per_species}")
    print(f"📂 Output: {output_dir}")
    
    confirm = input("\nStart batch scraping? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Batch scraping cancelled")
        return
    
    # Setup headless display
    display = setup_headless_display()
    
    try:
        # Run batch scraping with enhanced parameters
        batch_scraper = BatchFishScraper(csv_file, output_dir, images_per_species)
        priority_filter = priority if priority != 'ALL' else None
        
        batch_scraper.run_batch_scraping(
            start_index=start_row,
            max_species=max_species,
            priority_filter=priority_filter
        )
        
    except Exception as e:
        logger.error(f"Batch scraping failed: {e}")
        print(f"❌ Batch scraping failed: {e}")
    finally:
        if display:
            display.stop()

def parse_arguments():
    """Parse command line arguments for Ubuntu server mode"""
    parser = argparse.ArgumentParser(description='Fish Image Scraper - Ubuntu Server Edition')
    
    # Add subcommands
    subparsers = parser.add_subparsers(dest='mode', help='Scraping mode')
    
    # Single species mode
    single_parser = subparsers.add_parser('single', help='Single species scraping')
    single_parser.add_argument('species', help='Fish species name')
    single_parser.add_argument('--latin', help='Scientific/Latin name')
    single_parser.add_argument('--images', type=int, default=10, help='Target number of images (default: 10)')
    single_parser.add_argument('--folder', default='fish_images', help='Output folder (default: fish_images)')
    
    # Batch scraping mode
    batch_parser = subparsers.add_parser('batch', help='Batch scraping from CSV file')
    batch_parser.add_argument('--csv', default='fish_scraping_list_updated.csv', 
                             help='CSV file path (default: fish_scraping_list_updated.csv)')
    batch_parser.add_argument('--start-row', type=int, default=0, 
                             help='Start from row number (0-indexed, default: 0)')
    batch_parser.add_argument('--max-species', type=int, 
                             help='Maximum number of species to scrape')
    batch_parser.add_argument('--priority', choices=['HIGH', 'MEDIUM', 'LOW'], 
                             help='Filter by species priority')
    batch_parser.add_argument('--folder', default='fish_images', 
                             help='Output folder (default: fish_images)')
    batch_parser.add_argument('--images', type=int, default=10, 
                             help='Target images per species (default: 10)')
    
    # Test mode
    test_parser = subparsers.add_parser('test', help='Test mode with minimal scraping')
    test_parser.add_argument('--images', type=int, default=3, help='Test images count (default: 3)')
    test_parser.add_argument('--folder', default='test_images', help='Test output folder')
    
    return parser.parse_args()

def single_species_cli(args):
    """Command line single species mode"""
    print(f"🐟 UBUNTU SINGLE SPECIES SCRAPING: {args.species}")
    print("=" * 60)
    
    print(f"🎯 Target: {args.images} images for '{args.species}'")
    if args.latin:
        print(f"🔬 Latin name: {args.latin}")
    print(f"📂 Output: {args.folder}/{args.species.lower().replace(' ', '_')}")
    
    # Setup headless display
    display = setup_headless_display()
    
    try:
        # Start scraping
        scraper = FishImageScraper(args.species, args.images, args.folder, args.latin)
        downloaded = scraper.run_scraping()
        
        print(f"\n{'='*60}")
        if downloaded >= args.images:
            print(f"✅ SUCCESS! Downloaded {downloaded} images")
        else:
            print(f"⚠️ PARTIAL SUCCESS! Downloaded {downloaded}/{args.images} images")
        
        print(f"📁 Images saved in: {scraper.species_dir}")
        print(f"{'='*60}")
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        print(f"❌ Scraping failed: {e}")
    finally:
        if display:
            display.stop()

def batch_scraping_cli(args):
    """Command line batch scraping mode"""
    print(f"🐟 UBUNTU BATCH SCRAPING MODE")
    print("=" * 60)
    
    print(f"📁 CSV File: {args.csv}")
    print(f"📍 Start Row: {args.start_row}")
    print(f"📊 Max Species: {args.max_species or 'ALL'}")
    print(f"🏷️ Priority: {args.priority or 'ALL'}")
    print(f"📂 Output: {args.folder}")
    print(f"🎯 Images per species: {args.images}")
    
    # Setup headless display
    display = setup_headless_display()
    
    try:
        # Start batch scraping
        batch_scraper = BatchFishScraper(args.csv, args.folder, args.images)
        batch_scraper.run_batch_scraping(
            start_index=args.start_row,
            max_species=args.max_species,
            priority_filter=args.priority
        )
        
    except Exception as e:
        logger.error(f"Batch scraping failed: {e}")
        print(f"❌ Batch scraping failed: {e}")
    finally:
        if display:
            display.stop()

def test_mode_cli(args):
    """Command line test mode"""
    print(f"🧪 UBUNTU TEST MODE")
    print("=" * 40)
    
    # Setup headless display
    display = setup_headless_display()
    
    try:
        scraper = FishImageScraper("goldfish", args.images, args.folder, "Carassius auratus")
        downloaded = scraper.run_scraping()
        
        print(f"✅ Test completed: {downloaded}/{args.images} images downloaded")
        print(f"📁 Test images saved in: {scraper.species_dir}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"❌ Test failed: {e}")
    finally:
        if display:
            display.stop()

def main():
    """Main function for Ubuntu server mode"""
    
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    # Apply server optimizations
    optimize_for_server()
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Handle command line mode
    if args.mode:
        if args.mode == 'single':
            single_species_cli(args)
        elif args.mode == 'batch':
            batch_scraping_cli(args)
        elif args.mode == 'test':
            test_mode_cli(args)
        return
    
    # Interactive mode (backward compatibility)
    interactive_mode()

def interactive_mode():
    """Interactive mode for backward compatibility"""
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
    # Show usage examples if run with no arguments
    import sys
    if len(sys.argv) == 1:
        print("🐟 Fish Image Scraper - Ubuntu Server Edition 🐟")
        print("=" * 60)
        print("Optimized for headless server operation with enhanced Google Images!")
        print("=" * 60)
        
        print("\nCOMMAND LINE USAGE (Ubuntu Server):")
        print("\n1. Single Species Mode:")
        print("   python3 scraping_ubuntu.py single 'Arwana' --latin 'Scleropages formosus' --images 5")
        print("   python3 scraping_ubuntu.py single 'Nemo' --images 10 --folder server_fish_images")
        
        print("\n2. Batch Scraping Mode:")
        print("   python3 scraping_ubuntu.py batch --csv fish_scraping_top50.csv --start-row 10 --max-species 5")
        print("   python3 scraping_ubuntu.py batch --start-row 50 --priority HIGH --images 15")
        print("   python3 scraping_ubuntu.py batch --csv fish_scraping_list_updated.csv --start-row 100 --max-species 20")
        
        print("\n3. Test Mode:")
        print("   python3 scraping_ubuntu.py test --images 3")
        print("   python3 scraping_ubuntu.py test --folder test_output")
        
        print("\n4. Interactive Mode:")
        print("   python3 scraping_ubuntu.py  (tanpa parameter akan masuk ke interactive mode)")
        
        print("\nUBUNTU SERVER FEATURES:")
        print("✅ Headless operation (virtual display)")
        print("✅ Server optimizations (memory, concurrent limits)")
        print("✅ Enhanced logging for monitoring")
        print("✅ --start-row: Resume batch scraping dari baris tertentu")
        print("✅ --max-species: Batasi jumlah species")
        print("✅ --priority: Filter berdasarkan prioritas (HIGH/MEDIUM/LOW)")
        print("✅ --images: Target jumlah gambar per species")
        print("✅ Google Images FIX: Large high-quality images!")
        print("✅ Multiple sources: Wikimedia, Bing, Unsplash, Google Images")
        
        print("\nSERVER SETUP REQUIREMENTS:")
        print("- sudo apt-get install xvfb")
        print("- pip install pyvirtualdisplay (optional)")
        print("- Google Chrome/Chromium browser")
        print("- Stable internet connection")
        
        print("\nFor help: python3 scraping_ubuntu.py --help")
        print("For batch help: python3 scraping_ubuntu.py batch --help")
        print("For single help: python3 scraping_ubuntu.py single --help")
        print("")
    
    main()