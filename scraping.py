#!/usr/bin/env python3
"""
Fish Image Scraper
Scraping gambar ikan dengan input species dan minimum jumlah gambar
"""

import requests
from bs4 import BeautifulSoup
import os
import time
import random
from urllib.parse import urljoin, urlparse
from PIL import Image
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import argparse
import logging
from tqdm import tqdm
import urllib3
import pandas as pd
import json

# Disable SSL warnings for certain sites
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FishImageScraper:
    def __init__(self, species, min_images, output_dir="fish_images", scientific_name=None):
        self.species = species.lower().replace(" ", "_")
        self.scientific_name = scientific_name
        self.current_search_term = scientific_name or species  # Default to scientific name or species
        self.min_images = min_images
        self.output_dir = output_dir
        self.downloaded_count = 0
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Create directory structure
        self.species_dir = os.path.join(output_dir, self.species)
        os.makedirs(self.species_dir, exist_ok=True)
        
        # Check existing images in folder
        self.existing_count = self.count_existing_images()
        if self.existing_count > 0:
            logger.info(f"Found {self.existing_count} existing images in {self.species_dir}")
        
        # Valid image extensions (including webp for conversion)
        self.valid_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    
    def count_existing_images(self):
        """Count existing valid images in the species directory"""
        if not os.path.exists(self.species_dir):
            return 0
        
        count = 0
        for filename in os.listdir(self.species_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                filepath = os.path.join(self.species_dir, filename)
                if os.path.isfile(filepath):
                    count += 1
        return count
    
    def get_next_file_number(self):
        """Get the next file number for naming new images"""
        if not os.path.exists(self.species_dir):
            return 1
        
        max_num = 0
        pattern = f"{self.species}_"
        
        for filename in os.listdir(self.species_dir):
            if filename.startswith(pattern) and filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                try:
                    # Extract number from filename like "species_0001.jpg"
                    number_part = filename[len(pattern):].split('.')[0]
                    num = int(number_part)
                    max_num = max(max_num, num)
                except (ValueError, IndexError):
                    continue
        
        return max_num + 1
    
    def get_total_images(self):
        """Get total images including existing and newly downloaded"""
        return self.existing_count + self.downloaded_count
        
    def is_target_reached(self):
        """Check if target number of images is reached"""
        return self.get_total_images() >= self.min_images
        
    def get_remaining_needed(self):
        """Get number of images still needed to reach target"""
        total = self.get_total_images()
        return max(0, self.min_images - total)
        
    def is_valid_image_url(self, url):
        """Check if URL points to a valid image"""
        try:
            if not url or not url.startswith('http'):
                return False
            
            # Skip base64 images
            if url.startswith('data:'):
                return False
            
            parsed_url = urlparse(url.lower())
            path = parsed_url.path
            
            # Check file extension
            has_extension = any(path.endswith(ext) for ext in self.valid_extensions)
            
            # Skip irrelevant images (profile pics, logos, icons)
            unwanted_keywords = ['profile', 'avatar', 'logo', 'icon', 'button', 'banner', 'ad', 'thumb', 'favicon']
            if any(keyword in url.lower() for keyword in unwanted_keywords):
                return False
            
            # Also allow URLs that might serve images without clear extension
            # (many modern websites serve images through dynamic URLs)
            has_image_keywords = any(keyword in url.lower() for keyword in ['image', 'img', 'photo', 'picture'])
            
            return has_extension or has_image_keywords or len(path) == 0
        except:
            return False
    
    def download_image(self, url, filename):
        """Download and validate image"""
        try:
            response = self.session.get(url, timeout=10, stream=True)
            response.raise_for_status()
            
            # Check content type (including webp)
            content_type = response.headers.get('content-type', '').lower()
            if not any(img_type in content_type for img_type in ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']):
                logger.warning(f"Invalid content type: {content_type} for {url}")
                return False
            
            # Save temporary file
            temp_path = os.path.join(self.species_dir, f"temp_{filename}")
            
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Validate image with PIL
            try:
                with Image.open(temp_path) as img:
                    # Check minimum size
                    if img.width < 150 or img.height < 150:
                        os.remove(temp_path)
                        logger.warning(f"Image too small: {img.width}x{img.height}")
                        return False
                    
                    # Check aspect ratio (fish images shouldn't be too extreme)
                    aspect_ratio = max(img.width, img.height) / min(img.width, img.height)
                    if aspect_ratio > 5:  # Skip very elongated images
                        os.remove(temp_path)
                        logger.warning(f"Aspect ratio too extreme: {aspect_ratio:.2f}")
                        return False
                    
                    # Convert to RGB if needed (handles WEBP, PNG with transparency, etc.)
                    if img.mode in ('RGBA', 'LA', 'P') or img.format == 'WEBP':
                        img = img.convert('RGB')
                        logger.info(f"Converted {img.format} to RGB")
                    
                    # Get next file number (continues from existing images)
                    file_number = self.existing_count + self.downloaded_count + 1
                    
                    # Determine file extension based on original format
                    if content_type == 'image/png' and img.mode != 'RGB':
                        # Keep as PNG if it has transparency
                        final_path = os.path.join(self.species_dir, f"{self.species}_{file_number:04d}.png")
                        img.save(final_path, 'PNG', optimize=True)
                        logger.info(f"Saved PNG with transparency: {final_path}")
                    else:
                        # Convert everything else to JPG (including WEBP)
                        final_path = os.path.join(self.species_dir, f"{self.species}_{file_number:04d}.jpg")
                        img.save(final_path, 'JPEG', quality=95, optimize=True)
                        if img.format == 'WEBP':
                            logger.info(f"Converted WEBP to JPG: {final_path}")
                        else:
                            logger.info(f"Saved JPG: {final_path}")
                    
                os.remove(temp_path)
                self.downloaded_count += 1
                logger.info(f"Downloaded: {final_path}")
                return True
                
            except Exception as e:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                logger.error(f"Image validation failed: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Download failed for {url}: {e}")
            return False
    
    def get_driver(self):
        """Get WebDriver with fallback options for multiple browsers"""
        # Try Safari first (built-in macOS, no security issues)
        try:
            from selenium import webdriver
            safari_options = webdriver.SafariOptions()
            driver = webdriver.Safari(options=safari_options)
            logger.info("Using Safari WebDriver (most secure)")
            return driver
        except Exception as safari_error:
            logger.warning(f"Safari WebDriver not available: {safari_error}")
            
            # Try Firefox with geckodriver
            try:
                from selenium.webdriver.firefox.options import Options as FirefoxOptions
                from selenium.webdriver.firefox.service import Service as FirefoxService
                from webdriver_manager.firefox import GeckoDriverManager
                
                firefox_options = FirefoxOptions()
                firefox_options.add_argument('--headless')
                firefox_options.add_argument('--no-sandbox')
                firefox_options.add_argument('--disable-dev-shm-usage')
                
                firefox_service = FirefoxService(GeckoDriverManager().install())
                driver = webdriver.Firefox(service=firefox_service, options=firefox_options)
                logger.info("Using Firefox WebDriver")
                return driver
            except Exception as firefox_error:
                logger.warning(f"Firefox WebDriver not available: {firefox_error}")
                
                # Chrome with additional security options
                try:
                    chrome_options = Options()
                    chrome_options.add_argument('--headless')
                    chrome_options.add_argument('--no-sandbox')
                    chrome_options.add_argument('--disable-dev-shm-usage')
                    chrome_options.add_argument('--disable-gpu')
                    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                    chrome_options.add_argument('--disable-web-security')
                    chrome_options.add_argument('--allow-running-insecure-content')
                    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                    chrome_options.add_experimental_option('useAutomationExtension', False)
                    
                    service = Service(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                    logger.info("Using Chrome WebDriver with enhanced security")
                    
                    # Hide webdriver property
                    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                    return driver
                except Exception as chrome_error:
                    logger.error(f"All WebDriver options failed. Chrome error: {chrome_error}")
                    return None

    def extract_original_url_from_google(self, driver, img_element):
        """Extract original image URL from Google Images by clicking and inspecting preview"""
        try:
            # Scroll to image and click
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", img_element)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", img_element)
            time.sleep(3)
            
            # Look for the large preview image with different strategies
            original_url = None
            
            # Strategy 1: Check for data-iurl (most reliable)
            try:
                large_img = driver.find_element(By.CSS_SELECTOR, "img[data-iurl]")
                original_url = large_img.get_attribute('data-iurl')
                if original_url and not any(skip in original_url for skip in ['encrypted-tbn', 'gstatic', 'googleusercontent']):
                    return original_url
            except:
                pass
            
            # Strategy 2: Look for external domain URLs in src
            try:
                preview_imgs = driver.find_elements(By.CSS_SELECTOR, ".irc_mi img, .v4dQwb img, .iPVvYb img")
                for img in preview_imgs:
                    src_url = img.get_attribute('src')
                    if src_url and src_url.startswith('http') and not any(skip in src_url for skip in ['encrypted-tbn', 'gstatic', 'google']):
                        return src_url
            except:
                pass
            
            # Strategy 3: Check page metadata
            try:
                # Look for the "View image" link which contains original URL
                view_image_link = driver.find_element(By.XPATH, "//a[contains(text(), 'View image') or contains(@href, '/imgres?')]")
                href = view_image_link.get_attribute('href')
                if href:
                    import urllib.parse
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                    if 'imgurl' in parsed:
                        return parsed['imgurl'][0]
            except:
                pass
            
            # Strategy 4: Look in image context menu or page source
            try:
                # Execute JavaScript to find image context
                original_url = driver.execute_script("""
                    var imgs = document.querySelectorAll('img');
                    for (var i = 0; i < imgs.length; i++) {
                        var src = imgs[i].src;
                        if (src && src.indexOf('http') === 0 && 
                            src.indexOf('encrypted-tbn') === -1 && 
                            src.indexOf('gstatic') === -1 &&
                            src.indexOf('google') === -1) {
                            return src;
                        }
                    }
                    return null;
                """)
                if original_url:
                    return original_url
            except:
                pass
                
            return None
            
        except Exception as e:
            return None
        finally:
            # Always try to close the preview
            try:
                close_btn = driver.find_element(By.CSS_SELECTOR, "[aria-label*='Close'], .irc_cb, [title*='Close']")
                driver.execute_script("arguments[0].click();", close_btn)
            except:
                try:
                    # Press ESC key as fallback
                    driver.find_element(By.TAG_NAME, 'body').send_keys('\ue00c')
                except:
                    pass

    def get_larger_google_image_url(self, img_url):
        """Try to get larger version of Google Images URL - legacy fallback"""
        try:
            # Skip encrypted thumbnails entirely - they can't be enlarged
            if 'encrypted-tbn' in img_url or 'gstatic.com' in img_url:
                return None
            
            # For regular URLs, try to increase size parameters
            if '=w' in img_url and '=h' in img_url:
                import re
                img_url = re.sub(r'=w\d+', '=w1200', img_url)
                img_url = re.sub(r'=h\d+', '=h800', img_url)
            elif 's=' in img_url:
                img_url = re.sub(r's=\d+', 's=1200', img_url)
            elif any(size in img_url for size in ['150x150', '200x200', '300x300']):
                img_url = img_url.replace('150x150', '1200x800')
                img_url = img_url.replace('200x200', '1200x800')  
                img_url = img_url.replace('300x300', '1200x800')
            
            return img_url
        except:
            return img_url
    
    def scrape_google_images(self):
        """Scrape images from Google Images by extracting URLs from page source"""
        logger.info("Scraping Google Images...")
        
        driver = self.get_driver()
        if not driver:
            return
        
        try:
            # Use enhanced search URL with quality filters  
            search_query = self.latin_name if self.latin_name else self.current_search_term
            # Multiple filters: large size, color images, JPEG format, photos only
            url = f"https://www.google.com/search?q={search_query}&tbm=isch&tbs=isz:l,ic:color,ift:jpg,itp:photo"
            
            logger.info(f"🔍 Google Images search query (Large + Color + Photo): {search_query}")
            
            driver.get(url)
            time.sleep(4)
            
            # Scroll to load more images  
            for i in range(5):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                logger.debug(f"Scrolled {i+1} times")
            
            images_collected = 0
            processed_urls = set()
            
            # Extract URLs directly from page source (much more reliable!)
            logger.info("Extracting image URLs from page source...")
            page_source = driver.page_source
            
            # Multiple regex patterns to find external image URLs
            import re
            import urllib.parse
            
            url_patterns = [
                r'"(https?://[^"]+\.(?:jpg|jpeg|png|webp))"',  # Direct image URLs in quotes
                r'imgurl=([^&"]+)',  # imgurl parameters
                r'"ou":"([^"]+)"',   # ou (original URL) in JSON
                r'"murl":"([^"]+)"'  # murl in JSON metadata
            ]
            
            external_urls = set()
            for pattern in url_patterns:
                matches = re.findall(pattern, page_source)
                for match in matches:
                    # Decode URL if needed
                    try:
                        decoded_url = urllib.parse.unquote(match)
                        if (decoded_url.startswith('http') and 
                            any(ext in decoded_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp'])):
                            
                            # Skip Google hosted images
                            if not any(skip in decoded_url for skip in [
                                'encrypted-tbn', 'gstatic', 'googleusercontent', 
                                'google.com', 'ggpht', 'blogger.googleusercontent'
                            ]):
                                external_urls.add(decoded_url)
                    except:
                        continue
            
            # Also check script tags for JSON data
            try:
                script_elements = driver.find_elements(By.TAG_NAME, "script")
                for script in script_elements:
                    script_content = script.get_attribute('innerHTML')
                    if script_content:
                        # Find JSON-like patterns containing image URLs
                        json_matches = re.findall(r'\["([^"]+\.(?:jpg|jpeg|png|webp))"', script_content)
                        for match in json_matches:
                            if (match.startswith('http') and 
                                not any(skip in match for skip in ['encrypted-tbn', 'gstatic', 'google'])):
                                external_urls.add(match)
            except:
                pass
            
            logger.info(f"Found {len(external_urls)} external image URLs")
            
            # Download images from extracted URLs
            for i, img_url in enumerate(external_urls):
                if images_collected >= self.min_images:
                    break
                    
                if img_url not in processed_urls:
                    # Validate URL before downloading
                    if self.is_valid_image_url(img_url):
                        logger.info(f"Trying Google image [{i+1}]: {img_url[:80]}...")
                        
                        if self.download_image(img_url, f"google_{images_collected}.jpg"):
                            images_collected += 1
                            processed_urls.add(img_url)
                            logger.info(f"✅ Downloaded image {images_collected}")
                        else:
                            logger.debug(f"❌ Failed to download: {img_url[:50]}...")
                    else:
                        logger.debug(f"Invalid URL: {img_url[:50]}...")
                
                # Small delay to be respectful
                time.sleep(random.uniform(0.5, 1.5))
            
            logger.info(f"Google Images: {images_collected}/{self.min_images} images collected")
            self.downloaded_count += images_collected
            
        except Exception as e:
            logger.error(f"Error in Google Images scraping: {e}")
        finally:
            if driver:
                driver.quit()
    
    def scrape_bing_images(self):
        """Scrape images from Bing Images with improved selectors"""
        logger.info("Scraping Bing Images...")
        
        # Use only the Latin name - no additional keywords
        if not self.current_search_term:
            logger.error("No Latin name available for Bing Images search")
            return
            
        search_query = self.current_search_term.replace(' ', '%20')
        logger.info(f"🔍 Bing search query (Latin only): {search_query}")
        
        for page in range(0, min(3, (self.min_images // 35) + 1)):
            if self.is_target_reached():
                break
                
            try:
                # Better Bing Images URL with proper parameters
                url = f"https://www.bing.com/images/search?q={search_query}&form=HDRSC2&first={page * 35}&tsc=ImageBasicHover"
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                response = self.session.get(url, headers=headers, timeout=15)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for actual image data in JSON or data attributes
                import re
                import json
                
                # Method 1: Find images in script tags (more reliable)
                scripts = soup.find_all('script')
                img_urls_found = []
                
                for script in scripts:
                    if script.string:
                        # Look for image URLs in script content
                        matches = re.findall(r'"murl":"([^"]+\.(?:jpg|jpeg|png|webp))"', script.string)
                        img_urls_found.extend(matches)
                        
                        # Also look for other URL patterns
                        matches2 = re.findall(r'"turl":"([^"]+\.(?:jpg|jpeg|png|webp))"', script.string)
                        img_urls_found.extend(matches2)
                
                # Method 2: Look for img tags with better selectors
                img_elements = soup.find_all('img', {'class': lambda x: x and ('mimg' in x or 'iusc' in x)})
                
                for img in img_elements:
                    # Get metadata from parent elements
                    parent = img.find_parent('a') or img.find_parent('div')
                    if parent:
                        # Look for data attributes on parent
                        img_data = parent.get('m') or parent.get('data-m')
                        if img_data:
                            try:
                                data = json.loads(img_data)
                                if 'murl' in data:
                                    img_urls_found.append(data['murl'])
                                elif 'turl' in data:
                                    img_urls_found.append(data['turl'])
                            except:
                                pass
                
                # Remove duplicates and filter
                img_urls_found = list(set(img_urls_found))
                logger.info(f"Found {len(img_urls_found)} potential images on Bing page {page}")
                
                for i, img_url in enumerate(img_urls_found):
                    if self.is_target_reached():
                        break
                    
                    # Clean up URL
                    if img_url.startswith('\\'):
                        img_url = img_url.replace('\\', '')
                    
                    if self.is_valid_image_url(img_url):
                        logger.info(f"Trying Bing image: {img_url}")
                        if self.download_image(img_url, f"bing_{page}_{i}.jpg"):
                            pass
                        time.sleep(random.uniform(1, 2))
                        
            except Exception as e:
                logger.error(f"Bing scraping failed for page {page}: {e}")
            
            time.sleep(random.uniform(2, 4))
    
    def scrape_fishbase(self):
        """Scrape images from FishBase (specialized fish database)"""
        logger.info("Scraping FishBase...")
        
        try:
            # Use current search term (prioritizing Latin name)
            search_query = self.current_search_term.replace(' ', '+')
            search_url = f"https://www.fishbase.se/search.php?lang=English&SearchRequest_Name={search_query}"
            logger.info(f"🔍 FishBase search query: {self.current_search_term}")
            response = self.session.get(search_url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find fish species pages
            links = soup.find_all('a', href=True)
            fish_links = []
            
            for link in links:
                href = link.get('href')
                if href and 'summary' in href and 'SpecCode' in href:
                    fish_links.append(urljoin(search_url, href))
            
            for fish_link in fish_links[:3]:  # Limit to first 3 matches
                if self.downloaded_count >= self.min_images:
                    break
                    
                try:
                    response = self.session.get(fish_link, timeout=10)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Find images on the species page
                    img_tags = soup.find_all('img', src=True)
                    
                    for img in img_tags:
                        if self.downloaded_count >= self.min_images:
                            break
                            
                        img_url = img.get('src')
                        if img_url and self.is_valid_image_url(img_url):
                            if not img_url.startswith('http'):
                                img_url = urljoin(fish_link, img_url)
                            
                            self.download_image(img_url, f"fishbase_{fish_links.index(fish_link)}.jpg")
                            time.sleep(random.uniform(1, 2))
                            
                except Exception as e:
                    logger.error(f"Error scraping FishBase page {fish_link}: {e}")
                    
        except Exception as e:
            logger.error(f"FishBase scraping failed: {e}")
    
    def scrape_unsplash(self):
        """Scrape images from Unsplash with improved search"""
        logger.info("Scraping Unsplash...")
        
        try:
            # Use only the Latin name - no additional keywords
            if not self.current_search_term:
                logger.error("No Latin name available for Unsplash search")
                return
                
            search_query = self.current_search_term.replace(' ', '%20')
            
            # Try multiple search strategies for fish
            search_variations = [
                search_query,
                f"{search_query}%20fish",
                f"fish%20{search_query}",
            ]
            
            for variation in search_variations:
                if self.is_target_reached():
                    break
                    
                url = f"https://unsplash.com/napi/search/photos?query={variation}&per_page=30&page=1"
                logger.info(f"🔍 Unsplash API search: {variation}")
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Accept': 'application/json',
                }
                
                try:
                    response = self.session.get(url, headers=headers, timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        results = data.get('results', [])
                        
                        logger.info(f"Found {len(results)} images from Unsplash API")
                        
                        for i, result in enumerate(results):
                            if self.is_target_reached():
                                break
                            
                            # Get different sizes
                            urls = result.get('urls', {})
                            img_url = urls.get('regular') or urls.get('small') or urls.get('thumb')
                            
                            if img_url and self.is_valid_image_url(img_url):
                                logger.info(f"Trying Unsplash image: {img_url}")
                                if self.download_image(img_url, f"unsplash_{variation}_{i}.jpg"):
                                    pass
                                time.sleep(random.uniform(1, 2))
                                
                except Exception as api_error:
                    logger.warning(f"Unsplash API failed for {variation}: {api_error}")
                    
                    # Fallback to HTML scraping
                    try:
                        html_url = f"https://unsplash.com/s/photos/{variation}"
                        html_response = self.session.get(html_url, timeout=10)
                        soup = BeautifulSoup(html_response.content, 'html.parser')
                        
                        img_tags = soup.find_all('img', src=True)
                        
                        for i, img in enumerate(img_tags):
                            if self.is_target_reached():
                                break
                                
                            img_url = img.get('src')
                            if img_url and 'images.unsplash.com' in img_url:
                                # Skip profile images and small images
                                if 'profile-' in img_url or 'h=32' in img_url or 'w=32' in img_url:
                                    continue
                                
                                # Get higher resolution
                                if '?w=' in img_url:
                                    img_url = img_url.replace('?w=400', '?w=1080').replace('?w=200', '?w=1080')
                                
                                if self.is_valid_image_url(img_url):
                                    logger.info(f"Trying Unsplash HTML image: {img_url}")
                                    if self.download_image(img_url, f"unsplash_html_{i}.jpg"):
                                        pass
                                    time.sleep(random.uniform(1, 2))
                                    
                    except Exception as html_error:
                        logger.error(f"Unsplash HTML fallback failed: {html_error}")
                
                time.sleep(2)  # Rate limiting
                    
        except Exception as e:
            logger.error(f"Unsplash scraping failed: {e}")
    
    def scrape_simple_images(self):
        """Alternative image search using multiple search engines"""
        logger.info("Scraping alternative image sources...")
        
        try:
            # Use only the Latin name - no additional keywords
            if not self.current_search_term:
                logger.error("No search term available")
                return
                
            search_query = self.current_search_term.replace(' ', '+')
            logger.info(f"🔍 Alternative search query: {search_query}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            # Alternative search engines that are more reliable
            search_sources = [
                {
                    'name': 'Yandex',
                    'url': f"https://yandex.com/images/search?text={search_query}+fish",
                    'selector': 'img[src*="avatars.mds.yandex.net"]'
                },
                {
                    'name': 'Startpage',
                    'url': f"https://www.startpage.com/sp/search?query={search_query}+fish&cat=images",
                    'selector': 'img[src]'
                }
            ]
            
            for source in search_sources:
                if self.is_target_reached():
                    break
                    
                try:
                    logger.info(f"Trying {source['name']} images...")
                    response = self.session.get(source['url'], headers=headers, timeout=15, verify=False)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Extract image URLs using regex (more reliable)
                    import re
                    text = response.text
                    
                    # Look for various image URL patterns
                    patterns = [
                        r'https://[^"\s]*\.jpg',
                        r'https://[^"\s]*\.jpeg', 
                        r'https://[^"\s]*\.png',
                        r'https://[^"\s]*\.webp'
                    ]
                    
                    img_urls = []
                    for pattern in patterns:
                        matches = re.findall(pattern, text, re.IGNORECASE)
                        img_urls.extend(matches)
                    
                    # Remove duplicates and filter out unwanted URLs
                    img_urls = list(set(img_urls))
                    img_urls = [url for url in img_urls if not any(x in url.lower() for x in ['avatar', 'logo', 'icon', 'button', 'banner'])]
                    
                    logger.info(f"Found {len(img_urls)} potential images from {source['name']}")
                    
                    for i, img_url in enumerate(img_urls[:20]):
                        if self.is_target_reached():
                            break
                            
                        if self.is_valid_image_url(img_url):
                            logger.info(f"Trying {source['name']} image: {img_url}")
                            if self.download_image(img_url, f"{source['name'].lower()}_{i}.jpg"):
                                pass
                            time.sleep(random.uniform(1, 2))
                            
                except Exception as source_error:
                    logger.error(f"{source['name']} search failed: {source_error}")
                
                time.sleep(2)
                
        except Exception as e:
            logger.error(f"Alternative search failed: {e}")
    
    def scrape_wikimedia(self):
        """Scrape images from Wikimedia Commons (reliable source)"""
        logger.info("Scraping Wikimedia Commons...")
        
        try:
            # Use current search term (prioritizing Latin name)
            search_query = self.current_search_term
            logger.info(f"🔍 Wikimedia search query: {search_query}")
            # Search API for Wikimedia Commons
            api_url = f"https://commons.wikimedia.org/w/api.php"
            # Use current search term as primary
            search_terms = [search_query]
            
            # Add "fish" as fallback if not already included
            if 'fish' not in search_query.lower() and 'ikan' not in search_query.lower():
                search_terms.append(f"{search_query} fish")
            
            params = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': ' OR '.join(search_terms),
                'srnamespace': 6,  # File namespace
                'srlimit': 100
            }
            
            response = self.session.get(api_url, params=params, timeout=10)
            data = response.json()
            
            if 'query' in data and 'search' in data['query']:
                results = data['query']['search']
                logger.info(f"Found {len(results)} files on Wikimedia")
                
                for i, result in enumerate(results):
                    if self.downloaded_count >= self.min_images:
                        break
                    
                    filename = result['title']
                    if any(ext in filename.lower() for ext in ['.jpg', '.jpeg', '.png']):
                        # Get file info to get actual image URL
                        file_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{filename.replace('File:', '')}"
                        
                        logger.info(f"Trying Wikimedia image: {file_url}")
                        if self.download_image(file_url, f"wiki_{i}.jpg"):
                            pass
                        time.sleep(random.uniform(1, 2))
                        
        except Exception as e:
            logger.error(f"Wikimedia scraping failed: {e}")
    
    def scrape_flickr_images(self):
        """Scrape images from Flickr"""
        logger.info("Scraping Flickr...")
        
        try:
            if not self.current_search_term:
                logger.error("No search term available for Flickr")
                return
                
            search_query = self.current_search_term.replace(' ', '%20')
            
            # Search variations for fish
            search_terms = [
                search_query,
                f"{search_query}%20fish",
                f"fish%20{search_query}"
            ]
            
            for term in search_terms:
                if self.is_target_reached():
                    break
                    
                url = f"https://www.flickr.com/search/?text={term}"
                logger.info(f"🔍 Flickr search: {term}")
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
                
                try:
                    response = self.session.get(url, headers=headers, timeout=15)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Look for Flickr image patterns
                    img_tags = soup.find_all('img', src=True)
                    
                    for i, img in enumerate(img_tags):
                        if self.is_target_reached():
                            break
                            
                        img_url = img.get('src')
                        if img_url and 'flickr' in img_url and any(ext in img_url for ext in ['.jpg', '.jpeg', '.png']):
                            # Get larger version
                            if '_m.jpg' in img_url:
                                img_url = img_url.replace('_m.jpg', '_b.jpg')
                            elif '_s.jpg' in img_url:
                                img_url = img_url.replace('_s.jpg', '_b.jpg')
                            
                            if self.is_valid_image_url(img_url):
                                logger.info(f"Trying Flickr image: {img_url}")
                                if self.download_image(img_url, f"flickr_{term}_{i}.jpg"):
                                    pass
                                time.sleep(random.uniform(1, 2))
                                
                except Exception as e:
                    logger.error(f"Flickr search failed for {term}: {e}")
                
                time.sleep(2)
                
        except Exception as e:
            logger.error(f"Flickr scraping failed: {e}")
    
    def scrape_pexels_images(self):
        """Scrape images from Pexels"""
        logger.info("Scraping Pexels...")
        
        try:
            if not self.current_search_term:
                logger.error("No search term available for Pexels")
                return
                
            search_query = self.current_search_term.replace(' ', '%20')
            
            search_terms = [
                search_query,
                f"{search_query}%20fish",
                f"fish%20{search_query}"
            ]
            
            for term in search_terms:
                if self.is_target_reached():
                    break
                    
                url = f"https://www.pexels.com/search/{term}/"
                logger.info(f"🔍 Pexels search: {term}")
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
                
                try:
                    response = self.session.get(url, headers=headers, timeout=15)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Look for Pexels image patterns
                    img_tags = soup.find_all('img', src=True)
                    
                    for i, img in enumerate(img_tags):
                        if self.is_target_reached():
                            break
                            
                        img_url = img.get('src')
                        if img_url and 'pexels.com' in img_url and '/photos/' in img_url:
                            # Get higher resolution
                            if '?w=' in img_url:
                                img_url = img_url.split('?')[0]  # Remove parameters
                                img_url += '?w=1200&h=800&auto=compress'
                            
                            if self.is_valid_image_url(img_url):
                                logger.info(f"Trying Pexels image: {img_url}")
                                if self.download_image(img_url, f"pexels_{term}_{i}.jpg"):
                                    pass
                                time.sleep(random.uniform(1, 2))
                                
                except Exception as e:
                    logger.error(f"Pexels search failed for {term}: {e}")
                
                time.sleep(2)
                
        except Exception as e:
            logger.error(f"Pexels scraping failed: {e}")

    def scrape_pixabay_images(self):
        """Scrape images from Pixabay"""
        logger.info("Scraping Pixabay...")
        
        try:
            if not self.current_search_term:
                logger.error("No search term available for Pixabay")
                return
                
            search_query = self.current_search_term.replace(' ', '+')
            
            search_terms = [
                search_query,
                f"{search_query}+fish",
                f"fish+{search_query}"
            ]
            
            for term in search_terms:
                if self.is_target_reached():
                    break
                    
                url = f"https://pixabay.com/images/search/{term}/"
                logger.info(f"🔍 Pixabay search: {term}")
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
                
                try:
                    response = self.session.get(url, headers=headers, timeout=15)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Look for Pixabay image patterns
                    img_tags = soup.find_all('img', src=True)
                    
                    for i, img in enumerate(img_tags):
                        if self.is_target_reached():
                            break
                            
                        img_url = img.get('src')
                        if img_url and 'pixabay.com' in img_url and '/photo-' in img_url:
                            # Get higher resolution
                            if '_640.' in img_url:
                                img_url = img_url.replace('_640.', '_1280.')
                            elif '_150.' in img_url:
                                img_url = img_url.replace('_150.', '_1280.')
                            
                            if self.is_valid_image_url(img_url):
                                logger.info(f"Trying Pixabay image: {img_url}")
                                if self.download_image(img_url, f"pixabay_{term}_{i}.jpg"):
                                    pass
                                time.sleep(random.uniform(1, 2))
                                
                except Exception as e:
                    logger.error(f"Pixabay search failed for {term}: {e}")
                
                time.sleep(2)
                
        except Exception as e:
            logger.error(f"Pixabay scraping failed: {e}")

    def scrape_fish_specific_sites(self):
        """Scrape from fish-specific websites and databases"""
        logger.info("Scraping fish-specific websites...")
        
        try:
            # Use current search term (prioritizing Latin name)
            search_query = self.current_search_term.replace(' ', '+')
            logger.info(f"🔍 Fish sites search query: {search_query}")
            
            # Fish-specific websites to try
            fish_sites = [
                f"https://www.fishbase.se/search.php?SearchRequest_Name={search_query}",
                f"https://www.marinespecies.org/aphia.php?p=search&searchpar={search_query}",
            ]
            
            for site_url in fish_sites:
                if self.downloaded_count >= self.min_images:
                    break
                    
                try:
                    logger.info(f"Trying fish website: {site_url}")
                    response = self.session.get(site_url, timeout=15)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Find all images on the page
                    img_tags = soup.find_all('img', src=True)
                    
                    for img in img_tags:
                        if self.downloaded_count >= self.min_images:
                            break
                            
                        img_url = img.get('src')
                        if not img_url:
                            continue
                            
                        # Make URL absolute if needed
                        if img_url.startswith('/'):
                            from urllib.parse import urljoin
                            img_url = urljoin(site_url, img_url)
                        elif not img_url.startswith('http'):
                            continue
                        
                        # Check if image seems fish-related
                        img_alt = (img.get('alt') or '').lower()
                        img_title = (img.get('title') or '').lower()
                        
                        fish_keywords = ['fish', 'ikan', search_query.lower(), 'marine', 'aquatic']
                        if any(keyword in img_alt or keyword in img_title or keyword in img_url.lower() 
                               for keyword in fish_keywords):
                            
                            if self.is_valid_image_url(img_url):
                                logger.info(f"Found relevant fish image: {img_url}")
                                if self.download_image(img_url, f"fishsite_{self.downloaded_count}.jpg"):
                                    pass
                                time.sleep(random.uniform(2, 4))
                                
                except Exception as e:
                    logger.warning(f"Fish website scraping failed for {site_url}: {e}")
                    
        except Exception as e:
            logger.error(f"Fish-specific site scraping failed: {e}")
    
    def scrape_wikipedia_images(self, scientific_name=None):
        """Scrape images from Wikipedia articles about the fish species"""
        logger.info("Scraping Wikipedia images...")
        
        try:
            # Use current search term (prioritizing Latin name)
            primary_search = self.current_search_term
            logger.info(f"🔍 Wikipedia search query: {primary_search}")
            
            # Create search terms with current search term as priority
            search_terms = [
                primary_search,
                primary_search.replace(' ', '_'),
            ]
            
            # Add "fish" if not already included
            if 'fish' not in primary_search.lower():
                search_terms.append(f"{primary_search} fish")
            
            for search_term in search_terms:
                if self.downloaded_count >= self.min_images:
                    break
                    
                try:
                    # Wikipedia API search
                    search_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{search_term.replace(' ', '_')}"
                    response = self.session.get(search_url, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Get the main image if available
                        if 'originalimage' in data:
                            img_url = data['originalimage']['source']
                            if self.is_valid_image_url(img_url):
                                logger.info(f"Found Wikipedia image: {img_url}")
                                if self.download_image(img_url, f"wikipedia_main.jpg"):
                                    pass
                        
                        # Try to get the full page for more images
                        if 'content_urls' in data:
                            page_url = data['content_urls']['desktop']['page']
                            page_response = self.session.get(page_url, timeout=10)
                            page_soup = BeautifulSoup(page_response.content, 'html.parser')
                            
                            # Find images in the article
                            img_tags = page_soup.find_all('img', src=True)
                            
                            for img in img_tags:
                                if self.downloaded_count >= self.min_images:
                                    break
                                    
                                img_url = img.get('src')
                                if img_url and img_url.startswith('//'):
                                    img_url = 'https:' + img_url
                                
                                if img_url and self.is_valid_image_url(img_url):
                                    # Skip very small images (likely icons)
                                    if 'thumb' in img_url and ('150px' in img_url or '200px' in img_url):
                                        continue
                                        
                                    logger.info(f"Found Wikipedia page image: {img_url}")
                                    if self.download_image(img_url, f"wikipedia_{self.downloaded_count}.jpg"):
                                        pass
                                    time.sleep(random.uniform(1, 2))
                                    
                except Exception as e:
                    logger.warning(f"Wikipedia search failed for '{search_term}': {e}")
                    
        except Exception as e:
            logger.error(f"Wikipedia scraping failed: {e}")
    
    def scrape_indonesian_fish_sites(self):
        """Scrape from Indonesian fish databases and websites"""
        logger.info("Scraping Indonesian fish websites...")
        
        try:
            # Use current search term (prioritizing Latin name)
            search_query = self.current_search_term
            logger.info(f"🔍 Indonesian sites search query: {search_query}")
            
            # Indonesian fish-related websites
            indonesian_sites = [
                f"http://biodiversitywarriors.org/search?q={search_query}",
                f"https://kkp.go.id/search?keyword={search_query}",
                f"https://www.perpustakaan.kkp.go.id/search/{search_query}",
            ]
            
            for site_url in indonesian_sites:
                if self.downloaded_count >= self.min_images:
                    break
                    
                try:
                    logger.info(f"Trying Indonesian site: {site_url}")
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'id,en;q=0.5',
                    }
                    
                    response = self.session.get(site_url, headers=headers, timeout=15, verify=False)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Find all images
                    img_tags = soup.find_all('img', src=True)
                    
                    logger.info(f"Found {len(img_tags)} images on Indonesian site")
                    
                    for img in img_tags:
                        if self.downloaded_count >= self.min_images:
                            break
                            
                        img_url = img.get('src')
                        if not img_url:
                            continue
                            
                        # Make URL absolute
                        if img_url.startswith('/'):
                            from urllib.parse import urljoin
                            img_url = urljoin(site_url, img_url)
                        elif not img_url.startswith('http'):
                            continue
                        
                        # Check relevance
                        img_alt = (img.get('alt') or '').lower()
                        img_title = (img.get('title') or '').lower()
                        
                        relevant_keywords = ['ikan', 'fish', search_query.lower(), 'laut', 'air', 'aqua']
                        if any(keyword in img_alt or keyword in img_title or keyword in img_url.lower() 
                               for keyword in relevant_keywords):
                            
                            if self.is_valid_image_url(img_url):
                                logger.info(f"Found Indonesian fish image: {img_url}")
                                if self.download_image(img_url, f"indonesia_{self.downloaded_count}.jpg"):
                                    pass
                                time.sleep(random.uniform(2, 4))
                                
                except Exception as e:
                    logger.warning(f"Indonesian site scraping failed for {site_url}: {e}")
                    
        except Exception as e:
            logger.error(f"Indonesian fish site scraping failed: {e}")
    
    def run_scraping(self):
        """Main scraping function"""
        logger.info(f"Starting to scrape images for: {self.species}")
        logger.info(f"Target: {self.min_images} images")
        logger.info(f"Existing: {self.existing_count} images")
        logger.info(f"Need to download: {self.get_remaining_needed()} images")
        logger.info(f"Output directory: {self.species_dir}")
        
        # Check if we already have enough images
        if self.is_target_reached():
            logger.info(f"✅ Already have {self.get_total_images()} images (>= {self.min_images}). Skipping scraping.")
            return self.get_total_images()
        
        remaining_needed = self.get_remaining_needed()
        progress_bar = tqdm(total=remaining_needed, desc="Downloading images", initial=0)
        
        # Try different sources until we get enough images - prioritizing non-Wikipedia sources
        scrapers = [
            # self.scrape_unsplash,            # Free stock photos (good quality) ✅
            self.scrape_wikimedia,           # Wikimedia Commons
            self.scrape_wikipedia_images,    # Wikipedia articles (fixed parameter)
            self.scrape_bing_images,         # Bing images (improved) ✅
            self.scrape_google_images,       # Google images (improved)
            # self.scrape_pexels_images,       # Pexels stock photos
            # self.scrape_pixabay_images,      # Pixabay stock photos
            self.scrape_flickr_images,       # Flickr photos (high quality)
            # self.scrape_simple_images,       # Alternative search engines
            self.scrape_fishbase,            # Fish-specific database
            
        ]
        
        for scraper in scrapers:
            if self.is_target_reached():
                break
                
            initial_count = self.downloaded_count
            scraper()
            progress_bar.update(self.downloaded_count - initial_count)
            
            total_images = self.get_total_images()
            logger.info(f"Progress: {total_images}/{self.min_images} (existing: {self.existing_count}, downloaded: {self.downloaded_count})")
            
            if not self.is_target_reached():
                remaining = self.get_remaining_needed()
                logger.info(f"Still need {remaining} more images...")
                time.sleep(5)
        
        progress_bar.close()
        
        total_images = self.get_total_images()
        if self.is_target_reached():
            logger.info(f"✅ Successfully reached target! Total: {total_images} images (existing: {self.existing_count}, downloaded: {self.downloaded_count})")
        else:
            logger.warning(f"⚠️ Only reached {total_images}/{self.min_images} images (existing: {self.existing_count}, downloaded: {self.downloaded_count})")
        
        return total_images

class BatchFishScraper:
    """Batch scraper untuk scraping multiple species dari CSV file"""
    
    def __init__(self, csv_file, output_base_dir="fish_images", images_per_species=10):
        self.csv_file = csv_file
        self.output_base_dir = output_base_dir
        self.images_per_species = images_per_species
        self.results = []
        
    def load_fish_list(self):
        """Load fish list dari CSV file"""
        try:
            df = pd.read_csv(self.csv_file)
            logger.info(f"Loaded {len(df)} fish species from {self.csv_file}")
            return df
        except Exception as e:
            logger.error(f"Failed to load CSV file: {e}")
            return None
    
    def scrape_species(self, row, max_retries=2):
        """Scrape single species dengan retry mechanism menggunakan nama Latin sebagai prioritas"""
        species_name = row['species_indonesia']
        # Get scientific names from CSV (nama_latin field)
        # Field nama_latin now contains multiple latin names separated by ' ; '
        nama_latin_field = row.get('nama_latin') or ''
        # Split by ' ; ' first (new format), then by ';' and ',' for backward compatibility
        latin_names = []
        if ' ; ' in nama_latin_field:
            # New format with ' ; ' separator
            latin_names = [ln.strip() for ln in str(nama_latin_field).split(' ; ') if ln.strip()]
        else:
            # Old format with ';' or ',' separator
            latin_names = [ln.strip() for part in str(nama_latin_field).split(';') for ln in part.split(',') if ln.strip()]
        
        search_keywords = row.get('search_keywords', '')
        min_images = self.images_per_species  # Use configurable parameter instead of CSV
        
        # Create folder name using Indonesian name (cleaned)
        folder_species_name = species_name.lower().replace(' ', '_').replace('/', '_').replace('-', '_')

        logger.info(f"\n🐟 Starting scraping: {species_name}")
        logger.info(f"🔬 Latin names: {', '.join(latin_names) if latin_names else 'None'}")
        logger.info(f"📝 Fallback keywords: {search_keywords}")
        logger.info(f"🎯 Target: {min_images} images")
        logger.info(f"📁 Saving to folder: {folder_species_name}")
        
        # If no Latin names provided, log and return failed result
        if not latin_names:
            logger.warning(f"No Latin name found for {species_name} — skipping")
            return {
                'species_indonesia': species_name,
                'species_english': row.get('species_english', ''),
                'search_keyword_used': '',
                'target_images': min_images,
                'downloaded_images': 0,
                'success_rate': 0,
                'status': 'FAILED',
                'directory': '',
                'attempt': 0,
                'error': 'No Latin name'
            }

        # Try each latin name one-by-one until we reach min_images
        total_downloaded = 0
        attempts = 0
        for latin in latin_names:
            attempts += 1
            logger.info(f"🔍 Attempt {attempts}: Searching Latin name '{latin}' for {species_name}")

            try:
                # Create scraper that saves under the Indonesian folder name
                scraper = FishImageScraper(folder_species_name, min_images - total_downloaded, self.output_base_dir, latin)
                # Ensure the scraper uses the Latin name as the current search term
                scraper.current_search_term = latin

                downloaded = scraper.run_scraping()
                total_downloaded += downloaded

                # If reached target, return success
                if total_downloaded >= min_images:
                    logger.info(f"✅ SUCCESS! Got {total_downloaded}/{min_images} images for {species_name}")
                    return {
                        'species_indonesia': species_name,
                        'species_english': row.get('species_english', ''),
                        'search_keyword_used': latin,
                        'target_images': min_images,
                        'downloaded_images': total_downloaded,
                        'success_rate': (total_downloaded / min_images) * 100,
                        'status': 'SUCCESS',
                        'directory': scraper.species_dir,
                        'attempt': attempts
                    }

                # If not yet reached, continue to next latin name
                logger.info(f"⚠️ Collected {total_downloaded}/{min_images} so far for {species_name}; continuing with next Latin name if any")

            except Exception as e:
                logger.error(f"Attempt searching '{latin}' failed for {species_name}: {e}")
                # continue to next latin name
                continue

        # After trying all latin names, return partial result
        logger.warning(f"⚠️ Only downloaded {total_downloaded}/{min_images} images for {species_name} after trying all Latin names")
        return {
            'species_indonesia': species_name,
            'species_english': row.get('species_english', ''),
            'search_keyword_used': ';'.join(latin_names),
            'target_images': min_images,
            'downloaded_images': total_downloaded,
            'success_rate': (total_downloaded / min_images) * 100 if min_images else 0,
            'status': 'PARTIAL' if total_downloaded > 0 else 'FAILED',
            'directory': os.path.join(self.output_base_dir, folder_species_name),
            'attempt': attempts
        }
    
    def run_batch_scraping(self, start_index=0, max_species=None, priority_filter=None):
        """Run batch scraping untuk multiple species"""
        df = self.load_fish_list()
        if df is None:
            return
        
        # Filter berdasarkan prioritas jika diminta
        if priority_filter:
            df = df[df['prioritas'] == priority_filter]
            logger.info(f"Filtering by priority: {priority_filter} ({len(df)} species)")
        
        # Limit jumlah species jika diminta
        if max_species:
            df = df.iloc[start_index:start_index + max_species]
        else:
            df = df.iloc[start_index:]
        
        logger.info(f"🚀 Starting batch scraping for {len(df)} species...")
        
        # Progress tracking
        total_species = len(df)
        successful = 0
        partial = 0
        failed = 0
        
        for idx, (_, row) in enumerate(df.iterrows(), 1):
            print(f"\n{'='*70}")
            print(f"🐟 SPECIES {idx}/{total_species}: {row['species_indonesia']}")
            print(f"{'='*70}")
            
            result = self.scrape_species(row)
            self.results.append(result)
            
            # Update counters
            if result['status'] == 'SUCCESS':
                successful += 1
            elif result['status'] == 'PARTIAL':
                partial += 1
            else:
                failed += 1
            
            # Progress summary
            print(f"\n📊 PROGRESS SUMMARY:")
            print(f"✅ Success: {successful}/{total_species}")
            print(f"⚠️ Partial: {partial}/{total_species}")
            print(f"❌ Failed: {failed}/{total_species}")
            
            # Save progress setiap 5 species
            if idx % 5 == 0:
                self.save_progress()
            
            # Delay antar species
            time.sleep(random.uniform(3, 7))
        
        # Final report
        self.generate_final_report()
    
    def save_progress(self):
        """Save progress ke JSON file"""
        progress_file = f"scraping_progress_{int(time.time())}.json"
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        logger.info(f"Progress saved to: {progress_file}")
    
    def generate_final_report(self):
        """Generate laporan akhir batch scraping"""
        print(f"\n{'='*70}")
        print(f"📋 FINAL BATCH SCRAPING REPORT")
        print(f"{'='*70}")
        
        total = len(self.results)
        successful = len([r for r in self.results if r['status'] == 'SUCCESS'])
        partial = len([r for r in self.results if r['status'] == 'PARTIAL'])
        failed = len([r for r in self.results if r['status'] == 'FAILED'])
        
        print(f"Total Species Processed: {total}")
        print(f"✅ Successful: {successful} ({(successful/total)*100:.1f}%)")
        print(f"⚠️ Partial Success: {partial} ({(partial/total)*100:.1f}%)")
        print(f"❌ Failed: {failed} ({(failed/total)*100:.1f}%)")
        
        # Total images downloaded
        total_images = sum(r['downloaded_images'] for r in self.results)
        target_images = sum(r['target_images'] for r in self.results)
        print(f"\n📸 Images Downloaded: {total_images}/{target_images} ({(total_images/target_images)*100:.1f}%)")
        
        # Top performers
        if successful > 0:
            print(f"\n🏆 TOP SUCCESSFUL SPECIES:")
            success_results = [r for r in self.results if r['status'] == 'SUCCESS']
            success_results.sort(key=lambda x: x['downloaded_images'], reverse=True)
            for i, result in enumerate(success_results[:5], 1):
                print(f"{i}. {result['species_indonesia']}: {result['downloaded_images']} images")
        
        # Save detailed report
        report_file = f"batch_scraping_report_{int(time.time())}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'total_species': total,
                    'successful': successful,
                    'partial': partial,
                    'failed': failed,
                    'total_images_downloaded': total_images,
                    'target_images': target_images,
                    'success_rate': (successful/total)*100,
                    'completion_rate': (total_images/target_images)*100
                },
                'detailed_results': self.results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Detailed report saved to: {report_file}")

def batch_mode():
    """Interactive batch scraping mode"""
    print("🐟 Fish Batch Scraper 🐟")
    print("=" * 40)
    
    # Pilih file CSV
    csv_options = {
        '1': 'fish_scraping_top50.csv',
        '2': 'fish_scraping_list_updated.csv'
    }
    
    print("\nPilih fish database:")
    print("1. Top 50 Species (Recommended for testing)")
    print("2. All 1642 Species (Complete database)")
    
    while True:
        choice = input("Pilihan (1-2): ").strip()
        if choice in csv_options:
            csv_file = csv_options[choice]
            break
        print("❌ Pilihan tidak valid!")
    
    # Pilih prioritas
    print("\nPilih prioritas species:")
    print("1. HIGH priority only (Ikan populer)")
    print("2. MEDIUM priority only (Ikan sedang)")
    print("3. LOW priority only (Ikan langka)")
    print("4. ALL priorities")
    
    priority_map = {'1': 'HIGH', '2': 'MEDIUM', '3': 'LOW', '4': None}
    
    while True:
        choice = input("Pilihan (1-4): ").strip()
        if choice in priority_map:
            priority_filter = priority_map[choice]
            break
        print("❌ Pilihan tidak valid!")
    
    # Jumlah species
    max_species = input("\nJumlah species maksimal (kosong untuk semua): ").strip()
    max_species = int(max_species) if max_species.isdigit() else None
    
    # Start row option
    start_row = input("Mulai dari baris ke-berapa? (enter untuk mulai dari awal/0): ").strip()
    start_row = int(start_row) if start_row.isdigit() else 0
    
    # Images per species
    images_per_species = input("Target gambar per species (enter untuk 10): ").strip()
    images_per_species = int(images_per_species) if images_per_species.isdigit() else 10
    
    # Output directory
    output_dir = input("Output directory (enter untuk 'fish_images'): ").strip()
    if not output_dir:
        output_dir = "fish_images"
    
    print(f"\n🎯 BATCH SCRAPING SETUP:")
    print(f"📁 Database: {csv_file}")
    print(f"📍 Start Row: {start_row}")
    print(f"🏷️ Priority: {priority_filter or 'ALL'}")
    print(f"📊 Max species: {max_species or 'ALL'}")
    print(f"🎯 Images per species: {images_per_species}")
    print(f"📂 Output: {output_dir}")
    
    confirm = input("\nStart batch scraping? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Batch scraping cancelled")
        return
    
    # Start batch scraping
    batch_scraper = BatchFishScraper(csv_file, output_dir, images_per_species)
    batch_scraper.run_batch_scraping(
        start_index=start_row,
        max_species=max_species,
        priority_filter=priority_filter
    )

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Fish Image Scraper - Scraping gambar ikan dari berbagai sumber')
    
    # Add subcommands
    subparsers = parser.add_subparsers(dest='mode', help='Mode scraping')
    
    # Single species mode
    single_parser = subparsers.add_parser('single', help='Scraping untuk satu species')
    single_parser.add_argument('species', help='Nama species ikan')
    single_parser.add_argument('--latin', help='Nama latin/scientific name')
    single_parser.add_argument('--images', type=int, default=10, help='Minimum jumlah gambar (default: 10)')
    single_parser.add_argument('--folder', default='fish_images', help='Output folder (default: fish_images)')
    
    # Batch scraping mode
    batch_parser = subparsers.add_parser('batch', help='Batch scraping dari CSV file')
    batch_parser.add_argument('--csv', default='fish_scraping_list_updated.csv', 
                             help='Path ke CSV file (default: fish_scraping_list_updated.csv)')
    batch_parser.add_argument('--start-row', type=int, default=0, 
                             help='Mulai scraping dari baris ke-berapa (0-indexed, default: 0)')
    batch_parser.add_argument('--max-species', type=int, 
                             help='Maksimal jumlah species yang akan di-scraping')
    batch_parser.add_argument('--priority', choices=['HIGH', 'MEDIUM', 'LOW'], 
                             help='Filter berdasarkan prioritas species')
    batch_parser.add_argument('--folder', default='fish_images', 
                             help='Output folder (default: fish_images)')
    batch_parser.add_argument('--images', type=int, default=10, 
                             help='Target jumlah gambar per species (default: 10)')
    
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    # Jika tidak ada arguments, jalankan interactive mode
    if not args.mode:
        interactive_mode()
        return
    
    if args.mode == 'single':
        single_species_mode(args)
    elif args.mode == 'batch':
        batch_scraping_mode(args)

def interactive_mode():
    """Interactive mode untuk backward compatibility"""
    print("🐟 Fish Image Scraper 🐟")
    print("=" * 40)
    
    # Pilih mode
    print("\nPilih mode scraping:")
    print("1. Single Species (Manual input)")
    print("2. Batch Scraping (From CSV database)")
    
    while True:
        mode = input("Pilihan (1-2): ").strip()
        if mode in ['1', '2']:
            break
        print("❌ Pilihan tidak valid!")
    
    if mode == '2':
        batch_mode()
        return
    
    # Mode single species
    single_species_interactive()

def single_species_mode(args):
    """Command line mode untuk single species"""
    print(f"🐟 SINGLE SPECIES SCRAPING: {args.species}")
    print("=" * 50)
    
    print(f"🎯 Target: {args.images} images untuk '{args.species}'")
    if args.latin:
        print(f"🔬 Latin name: {args.latin}")
    print(f"📂 Output: {args.folder}/{args.species.lower().replace(' ', '_')}")
    
    # Start scraping
    scraper = FishImageScraper(args.species, args.images, args.folder, args.latin)
    
    try:
        downloaded = scraper.run_scraping()
        
        print(f"\n{'='*50}")
        if downloaded >= args.images:
            print(f"✅ SUCCESS! Downloaded {downloaded} images")
        else:
            print(f"⚠️ PARTIAL SUCCESS! Downloaded {downloaded}/{args.images} images")
        
        print(f"📁 Images saved in: {scraper.species_dir}")
        print(f"{'='*50}")
        
    except KeyboardInterrupt:
        print("\n❌ Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Scraping failed: {e}")

def batch_scraping_mode(args):
    """Command line mode untuk batch scraping"""
    print(f"🐟 BATCH SCRAPING MODE")
    print("=" * 50)
    
    print(f"📁 CSV File: {args.csv}")
    print(f"📍 Start Row: {args.start_row}")
    print(f"📊 Max Species: {args.max_species or 'ALL'}")
    print(f"🏷️ Priority: {args.priority or 'ALL'}")
    print(f"📂 Output: {args.folder}")
    print(f"🎯 Images per species: {args.images}")
    
    # Confirm before starting
    confirm = input("\nStart batch scraping? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Batch scraping cancelled")
        return
    
    # Start batch scraping
    batch_scraper = BatchFishScraper(args.csv, args.folder, args.images)
    batch_scraper.run_batch_scraping(
        start_index=args.start_row,
        max_species=args.max_species,
        priority_filter=args.priority
    )

def single_species_interactive():
    """Interactive mode untuk single species"""
    print("\n--- SINGLE SPECIES MODE ---")
    
    # Interactive input
    while True:
        species = input("Masukkan nama species ikan: ").strip()
        if species:
            break
        print("❌ Nama species tidak boleh kosong!")
    
    # Optional scientific name
    scientific_name = input("Masukkan nama ilmiah/scientific name (opsional): ").strip()
    if not scientific_name:
        scientific_name = None
    
    while True:
        try:
            min_images = int(input("Minimum jumlah gambar yang ingin di-scraping: ").strip())
            if min_images > 0:
                break
            else:
                print("❌ Jumlah gambar harus lebih dari 0!")
        except ValueError:
            print("❌ Masukkan angka yang valid!")
    
    # Optional output directory
    output_dir = input("Output directory (enter untuk 'fish_images'): ").strip()
    if not output_dir:
        output_dir = "fish_images"
    
    print(f"\n🎯 Target: {min_images} images untuk '{species}'")
    print(f"� Output: {output_dir}/{species.lower().replace(' ', '_')}")
    
    confirmation = input("\nProceed with scraping? (y/n): ").strip().lower()
    if confirmation != 'y':
        print("❌ Scraping cancelled")
        return
    
    # Start scraping
    scraper = FishImageScraper(species, min_images, output_dir, scientific_name)
    
    try:
        downloaded = scraper.run_scraping()
        
        print(f"\n{'='*50}")
        if downloaded >= min_images:
            print(f"✅ SUCCESS! Downloaded {downloaded} images")
        else:
            print(f"⚠️ PARTIAL SUCCESS! Downloaded {downloaded}/{min_images} images")
        
        print(f"📁 Images saved in: {scraper.species_dir}")
        print(f"{'='*50}")
        
    except KeyboardInterrupt:
        print("\n❌ Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Scraping failed: {e}")

if __name__ == "__main__":
    # Show usage examples if run with --help or no arguments
    import sys
    if len(sys.argv) == 1:
        print("🐟 Fish Image Scraper 🐟")
        print("=" * 50)
        print("\nCOMMAND LINE USAGE:")
        print("\n1. Single Species Mode:")
        print("   python scraping.py single 'Arwana' --latin 'Scleropages formosus' --images 5")
        print("   python scraping.py single 'Nemo' --images 10 --folder my_fish_images")
        
        print("\n2. Batch Scraping Mode:")
        print("   python scraping.py batch --csv fish_scraping_top50.csv --start-row 10 --max-species 5")
        print("   python scraping.py batch --start-row 50 --priority HIGH --images 15")
        print("   python scraping.py batch --csv fish_scraping_list_updated.csv --start-row 100 --max-species 20")
        
        print("\n3. Interactive Mode:")
        print("   python scraping.py  (tanpa parameter akan masuk ke interactive mode)")
        
        print("\nKEY FEATURES:")
        print("✅ --start-row: Mulai scraping dari baris ke-berapa di CSV (0-indexed)")
        print("✅ --max-species: Batasi jumlah species yang akan di-scraping")
        print("✅ --priority: Filter berdasarkan prioritas (HIGH/MEDIUM/LOW)")
        print("✅ --images: Tentukan target jumlah gambar per species")
        print("✅ Multiple source support: Google Images (FIXED!), Wikimedia, Bing, Unsplash")
        
        print("\nUntuk help lengkap: python scraping.py --help")
        print("Untuk help batch mode: python scraping.py batch --help")
        print("Untuk help single mode: python scraping.py single --help")
        print("")
    
    main()