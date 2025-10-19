#!/usr/bin/env python3
"""
Test komprehensif semua scraper untuk memastikan Google Images fix bekerja dalam sistem lengkap
"""

import logging
import sys
import os
from PIL import Image
from scraping import FishImageScraper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def analyze_image_sizes(directory):
    """Analyze sizes of downloaded images"""
    if not os.path.exists(directory):
        return []
    
    sizes = []
    for filename in os.listdir(directory):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            try:
                filepath = os.path.join(directory, filename)
                with Image.open(filepath) as img:
                    width, height = img.size
                    file_size = os.path.getsize(filepath)
                    sizes.append({
                        'filename': filename,
                        'width': width,
                        'height': height,
                        'pixels': width * height,
                        'file_size_kb': file_size // 1024
                    })
            except Exception as e:
                logger.error(f"Error analyzing {filename}: {e}")
    
    return sizes

def test_all_scrapers(species_name, latin_name, min_images=3):
    """Test all scrapers including the fixed Google Images"""
    logger.info(f"\n{'='*80}")
    logger.info(f"🧪 COMPREHENSIVE SCRAPER TEST: {species_name} ({latin_name})")
    logger.info(f"{'='*80}")
    
    # Create test folder
    folder_name = f"test_all_{species_name.lower().replace(' ', '_')}"
    test_dir = f"test_images/{folder_name}"
    
    # Clear existing test images
    if os.path.exists(test_dir):
        import shutil
        shutil.rmtree(test_dir)
    
    try:
        # Create scraper instance
        scraper = FishImageScraper(folder_name, min_images, "test_images", latin_name)
        scraper.current_search_term = latin_name
        scraper.latin_name = latin_name
        
        logger.info(f"📁 Test directory: {test_dir}")
        logger.info(f"🎯 Target: {min_images} images per source")
        logger.info(f"🔬 Latin name: {latin_name}")
        
        # Test semua scraper
        results = {}
        
        # 1. Test Wikimedia Commons
        logger.info(f"\n🔍 Testing Wikimedia Commons...")
        initial_count = scraper.downloaded_count
        scraper.scrape_wikimedia()
        wikimedia_downloaded = scraper.downloaded_count - initial_count
        results['wikimedia'] = wikimedia_downloaded
        logger.info(f"✅ Wikimedia Commons: {wikimedia_downloaded} images")
        
        # 2. Test Google Images (yang sudah diperbaiki!)
        logger.info(f"\n🔍 Testing Google Images (FIXED VERSION)...")
        initial_count = scraper.downloaded_count
        scraper.scrape_google_images()
        google_downloaded = scraper.downloaded_count - initial_count
        results['google'] = google_downloaded
        logger.info(f"✅ Google Images: {google_downloaded} images")
        
        # 3. Test Bing Images
        logger.info(f"\n🔍 Testing Bing Images...")
        initial_count = scraper.downloaded_count
        scraper.scrape_bing_images()
        bing_downloaded = scraper.downloaded_count - initial_count
        results['bing'] = bing_downloaded
        logger.info(f"✅ Bing Images: {bing_downloaded} images")
        
        # 4. Test Unsplash
        logger.info(f"\n🔍 Testing Unsplash...")
        initial_count = scraper.downloaded_count
        scraper.scrape_unsplash()
        unsplash_downloaded = scraper.downloaded_count - initial_count
        results['unsplash'] = unsplash_downloaded
        logger.info(f"✅ Unsplash: {unsplash_downloaded} images")
        
        # Analyze image quality
        logger.info(f"\n📊 ANALYZING DOWNLOADED IMAGES...")
        sizes = analyze_image_sizes(test_dir)
        
        if sizes:
            total_images = len(sizes)
            avg_width = sum(s['width'] for s in sizes) / len(sizes)
            avg_height = sum(s['height'] for s in sizes) / len(sizes)
            avg_file_size = sum(s['file_size_kb'] for s in sizes) / len(sizes)
            
            logger.info(f"📊 Total images downloaded: {total_images}")
            logger.info(f"📐 Average dimensions: {avg_width:.0f} x {avg_height:.0f} pixels")
            logger.info(f"📦 Average file size: {avg_file_size:.1f} KB")
            
            # Categorize by size
            large_images = [s for s in sizes if s['width'] >= 800 and s['height'] >= 600]
            medium_images = [s for s in sizes if s['width'] >= 400 and s['height'] >= 300 and s not in large_images]
            small_images = [s for s in sizes if s not in large_images and s not in medium_images]
            
            logger.info(f"\n🎯 QUALITY DISTRIBUTION:")
            logger.info(f"   🟢 Large (≥800x600): {len(large_images)} images ({len(large_images)/total_images*100:.1f}%)")
            logger.info(f"   🟡 Medium (≥400x300): {len(medium_images)} images ({len(medium_images)/total_images*100:.1f}%)")
            logger.info(f"   🔴 Small (<400x300): {len(small_images)} images ({len(small_images)/total_images*100:.1f}%)")
            
            # Identify Google Images in the results
            google_images = [s for s in sizes if 'google' in s['filename']]
            if google_images:
                google_avg_width = sum(s['width'] for s in google_images) / len(google_images)
                google_avg_height = sum(s['height'] for s in google_images) / len(google_images)
                logger.info(f"\n🎯 GOOGLE IMAGES QUALITY CHECK:")
                logger.info(f"   📊 Google images downloaded: {len(google_images)}")
                logger.info(f"   📐 Google average size: {google_avg_width:.0f} x {google_avg_height:.0f} pixels")
                
                if google_avg_width >= 800:
                    logger.info(f"   ✅ Google Images: EXCELLENT quality (large images)")
                elif google_avg_width >= 400:
                    logger.info(f"   ⚠️ Google Images: GOOD quality (medium images)")
                else:
                    logger.info(f"   ❌ Google Images: POOR quality (small images)")
        
        return {
            'species': species_name,
            'latin': latin_name,
            'results': results,
            'total_images': len(sizes) if sizes else 0,
            'avg_width': sum(s['width'] for s in sizes) / len(sizes) if sizes else 0,
            'avg_height': sum(s['height'] for s in sizes) / len(sizes) if sizes else 0,
            'sizes': sizes
        }
        
    except Exception as e:
        logger.error(f"❌ Test failed for {species_name}: {e}")
        return {
            'species': species_name,
            'latin': latin_name,
            'error': str(e)
        }

def main():
    """Main test function"""
    logger.info("🧪 COMPREHENSIVE SCRAPER TEST - GOOGLE IMAGES FIX VALIDATION")
    logger.info("=" * 90)
    
    # Test dengan species yang biasanya ada banyak gambar
    test_case = ("Goldfish", "Carassius auratus")
    
    result = test_all_scrapers(test_case[0], test_case[1], min_images=3)
    
    # Final assessment
    logger.info(f"\n{'='*90}")
    logger.info("📊 FINAL COMPREHENSIVE TEST RESULTS:")
    logger.info(f"{'='*90}")
    
    if 'error' in result:
        logger.info(f"❌ Test failed: {result['error']}")
    else:
        logger.info(f"🐟 Species: {result['species']} ({result['latin']})")
        logger.info(f"📊 Total images: {result['total_images']}")
        logger.info(f"📐 Average size: {result['avg_width']:.0f} x {result['avg_height']:.0f} pixels")
        
        logger.info(f"\n📈 SCRAPER PERFORMANCE:")
        for source, count in result['results'].items():
            status = "✅ Working" if count > 0 else "❌ Failed"
            logger.info(f"   {source.title()}: {count} images - {status}")
        
        # Overall quality assessment
        if result['avg_width'] >= 800:
            logger.info(f"\n🎯 OVERALL QUALITY: ✅ EXCELLENT (Large images)")
        elif result['avg_width'] >= 400:
            logger.info(f"\n🎯 OVERALL QUALITY: ⚠️ GOOD (Medium images)")
        else:
            logger.info(f"\n🎯 OVERALL QUALITY: ❌ POOR (Small images)")
        
        # Specific Google Images assessment
        google_count = result['results'].get('google', 0)
        if google_count > 0:
            google_images = [s for s in result['sizes'] if 'google' in s['filename']]
            if google_images:
                google_avg = sum(s['width'] for s in google_images) / len(google_images)
                logger.info(f"\n🔥 GOOGLE IMAGES FIX STATUS:")
                if google_avg >= 800:
                    logger.info(f"   ✅ SUCCESS! Google Images now downloads LARGE images ({google_avg:.0f}px average)")
                else:
                    logger.info(f"   ⚠️ Partial success. Google Images downloads {google_avg:.0f}px average")
            else:
                logger.info(f"\n🔥 GOOGLE IMAGES FIX STATUS:")
                logger.info(f"   ✅ Working but no Google images in final results")
        else:
            logger.info(f"\n🔥 GOOGLE IMAGES FIX STATUS:")
            logger.info(f"   ❌ Google Images not working")

if __name__ == "__main__":
    main()