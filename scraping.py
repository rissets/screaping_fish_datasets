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
        
        # Valid image extensions
        self.valid_extensions = {'.jpg', '.jpeg', '.png'}
        
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
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not any(img_type in content_type for img_type in ['image/jpeg', 'image/jpg', 'image/png']):
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
                    
                    # Convert to RGB if needed and save as JPG
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')
                    
                    final_path = os.path.join(self.species_dir, f"{self.species}_{self.downloaded_count + 1:04d}.jpg")
                    img.save(final_path, 'JPEG', quality=95)
                    
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
    
    def scrape_google_images(self):
        """Scrape images from Google Images using Selenium"""
        logger.info("Scraping Google Images...")
        
        # Try Safari first (built-in macOS, no security issues)
        driver = None
        
        # Option 1: Try Safari WebDriver (safest for macOS)
        try:
            from selenium import webdriver
            safari_options = webdriver.SafariOptions()
            driver = webdriver.Safari(options=safari_options)
            logger.info("Using Safari WebDriver (most secure)")
        except Exception as safari_error:
            logger.warning(f"Safari WebDriver not available: {safari_error}")
            
            # Option 2: Try Firefox with geckodriver
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
            except Exception as firefox_error:
                logger.warning(f"Firefox WebDriver not available: {firefox_error}")
                
                # Option 3: Chrome with additional security options
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
                    
                    # Use ChromeDriverManager without cache_valid_range (deprecated parameter)
                    service = Service(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                    logger.info("Using Chrome WebDriver with enhanced security")
                except Exception as chrome_error:
                    logger.error(f"All WebDriver options failed. Chrome error: {chrome_error}")
                    return
        
        if not driver:
            logger.error("No WebDriver available. Skipping Google Images.")
            return
        
        try:
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            # Use current search term (prioritizing Latin name)
            search_query = self.current_search_term
            url = f"https://www.google.com/search?q={search_query}&tbm=isch"
            
            logger.info(f"🔍 Google Images search query: {search_query}")
            
            driver.get(url)
            time.sleep(2)
            
            # Scroll and load more images
            last_height = driver.execute_script("return document.body.scrollHeight")
            images_collected = 0
            
            while self.downloaded_count < self.min_images and images_collected < self.min_images * 3:
                # Scroll down
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # Try to click "Show more results" button
                try:
                    show_more = driver.find_element(By.CSS_SELECTOR, "input[value='Show more results']")
                    driver.execute_script("arguments[0].click();", show_more)
                    time.sleep(3)
                except:
                    pass
                
                # Get image elements with better selectors
                images = driver.find_elements(By.CSS_SELECTOR, "img")
                
                for img in images:
                    if self.downloaded_count >= self.min_images:
                        break
                    
                    # Try multiple attributes to get image URL
                    img_url = (img.get_attribute('data-src') or 
                              img.get_attribute('src') or 
                              img.get_attribute('data-original') or
                              img.get_attribute('data-lazy-src'))
                    
                    if img_url and img_url.startswith('http') and self.is_valid_image_url(img_url):
                        # Skip small images (likely thumbnails)
                        try:
                            width = int(img.get_attribute('width') or 0)
                            height = int(img.get_attribute('height') or 0)
                            if width < 200 or height < 200:
                                continue
                        except:
                            pass
                        
                        logger.info(f"Attempting to download: {img_url}")
                        if self.download_image(img_url, f"google_{images_collected}.jpg"):
                            images_collected += 1
                        time.sleep(random.uniform(1, 2))
                
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                
        except Exception as e:
            logger.error(f"Google Images scraping failed: {e}")
        finally:
            try:
                driver.quit()
            except:
                pass
    
    def scrape_bing_images(self):
        """Scrape images from Bing Images"""
        logger.info("Scraping Bing Images...")
        
        # Use current search term (prioritizing Latin name)
        search_query = self.current_search_term
        logger.info(f"🔍 Bing search query: {search_query}")
        
        for page in range(0, min(5, (self.min_images // 35) + 1)):
            if self.downloaded_count >= self.min_images:
                break
                
            try:
                url = f"https://www.bing.com/images/search?q={search_query}&first={page * 35}"
                response = self.session.get(url, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Try multiple selectors for Bing images
                img_tags = (soup.find_all('img', {'class': 'mimg'}) + 
                           soup.find_all('img', src=True) + 
                           soup.find_all('img', {'data-src': True}))
                
                logger.info(f"Found {len(img_tags)} images on Bing page {page}")
                
                for i, img in enumerate(img_tags):
                    if self.downloaded_count >= self.min_images:
                        break
                        
                    img_url = (img.get('data-src') or img.get('src') or 
                              img.get('data-original') or img.get('data-srcset'))
                    
                    if img_url and 'http' in img_url:
                        # Clean up URL
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        elif img_url.startswith('/'):
                            img_url = 'https://www.bing.com' + img_url
                        
                        # Take first URL if srcset
                        if ' ' in img_url:
                            img_url = img_url.split(' ')[0]
                            
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
        """Scrape images from Unsplash (free stock photos)"""
        logger.info("Scraping Unsplash...")
        
        try:
            # Use current search term (prioritizing Latin name)
            search_query = self.current_search_term
            url = f"https://unsplash.com/s/photos/{search_query}"
            logger.info(f"🔍 Unsplash search query: {search_query}")
            
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find image containers
            img_tags = soup.find_all('img', src=True)
            
            logger.info(f"Found {len(img_tags)} images on Unsplash")
            
            for i, img in enumerate(img_tags):
                if self.downloaded_count >= self.min_images:
                    break
                    
                img_url = img.get('src')
                if img_url and 'unsplash' in img_url:
                    # Skip profile images and small images
                    if 'profile-' in img_url or 'h=32' in img_url or 'w=32' in img_url:
                        continue
                    
                    # Only process actual photo URLs
                    if '/photo-' in img_url or '/uploads/' in img_url:
                        # Get higher resolution version
                        if '?w=' in img_url:
                            img_url = img_url.replace('?w=400', '?w=1080').replace('?w=200', '?w=1080')
                        
                        if self.is_valid_image_url(img_url):
                            logger.info(f"Trying Unsplash image: {img_url}")
                            if self.download_image(img_url, f"unsplash_{i}.jpg"):
                                pass
                            time.sleep(random.uniform(1, 2))
                    
        except Exception as e:
            logger.error(f"Unsplash scraping failed: {e}")
    
    def scrape_simple_images(self):
        """Simple image search using DuckDuckGo (no JavaScript needed)"""
        logger.info("Scraping DuckDuckGo Images...")
        
        try:
            # Use current search term (prioritizing Latin name)
            search_query = self.current_search_term
            url = f"https://duckduckgo.com/?q={search_query}&t=h_&iax=images&ia=images"
            logger.info(f"🔍 DuckDuckGo search query: {search_query}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            # Disable SSL verification for DuckDuckGo
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            
            # Extract image URLs from the page
            import re
            img_urls = re.findall(r'https://[^"]*\.(?:jpg|jpeg|png)', response.text)
            
            logger.info(f"Found {len(img_urls)} potential images")
            
            for i, img_url in enumerate(img_urls[:50]):  # Limit to first 50
                if self.downloaded_count >= self.min_images:
                    break
                    
                if self.is_valid_image_url(img_url):
                    logger.info(f"Trying image: {img_url}")
                    if self.download_image(img_url, f"simple_{i}.jpg"):
                        pass
                    time.sleep(random.uniform(1, 2))
                    
        except Exception as e:
            logger.error(f"Simple scraping failed: {e}")
    
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
                'srlimit': 50
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
    
    def scrape_fish_specific_sites(self):
        """Scrape from fish-specific websites and databases"""
        logger.info("Scraping fish-specific websites...")
        
        try:
            # Use current search term (prioritizing Latin name)
            search_query = self.current_search_term
            logger.info(f"🔍 Fish sites search query: {search_query}")
            
            # Fish-specific websites to try
            fish_sites = [
                f"https://www.fisheries.go.id/search?q={search_query}",
                f"https://www.indonesianfishes.org/search/{search_query}",
                f"https://www.iucnredlist.org/search?query={search_query}",
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
        logger.info(f"Output directory: {self.species_dir}")
        
        progress_bar = tqdm(total=self.min_images, desc="Downloading images")
        
        # Try different sources until we get enough images
        scrapers = [
            lambda: self.scrape_wikipedia_images(self.scientific_name),    # Wikipedia articles (reliable, relevant)
            self.scrape_wikimedia,           # Wikimedia Commons (reliable, free)
            self.scrape_indonesian_fish_sites, # Indonesian fish databases
            self.scrape_fish_specific_sites, # Fish-specific websites
            self.scrape_unsplash,            # Free stock photos
            self.scrape_bing_images,         # Bing images
            self.scrape_simple_images,       # DuckDuckGo (with SSL fix)
            self.scrape_fishbase,            # Fish-specific database
            self.scrape_google_images,       # Google images (last resort)
        ]
        
        for scraper in scrapers:
            if self.downloaded_count >= self.min_images:
                break
                
            initial_count = self.downloaded_count
            scraper()
            progress_bar.update(self.downloaded_count - initial_count)
            
            logger.info(f"Progress: {self.downloaded_count}/{self.min_images}")
            
            if self.downloaded_count < self.min_images:
                logger.info("Retrying with more aggressive scraping...")
                time.sleep(5)
        
        progress_bar.close()
        
        if self.downloaded_count >= self.min_images:
            logger.info(f"✅ Successfully downloaded {self.downloaded_count} images!")
        else:
            logger.warning(f"⚠️ Only downloaded {self.downloaded_count}/{self.min_images} images")
        
        return self.downloaded_count

class BatchFishScraper:
    """Batch scraper untuk scraping multiple species dari CSV file"""
    
    def __init__(self, csv_file, output_base_dir="fish_images"):
        self.csv_file = csv_file
        self.output_base_dir = output_base_dir
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
        nama_latin = row['nama_latin']  # Primary search term
        search_keywords = row['search_keywords']
        min_images = row['min_images']
        
        # Create folder name using Indonesian name (cleaned)
        folder_species_name = species_name.lower().replace(' ', '_').replace('/', '_').replace('-', '_')
        
        logger.info(f"\n🐟 Starting scraping: {species_name}")
        logger.info(f"� Latin name (primary): {nama_latin}")
        logger.info(f"�📝 Fallback keywords: {search_keywords}")
        logger.info(f"🎯 Target: {min_images} images")
        logger.info(f"📁 Saving to folder: {folder_species_name}")
        
        # Split search strategies (primary = Latin name)
        search_strategies = search_keywords.split(';')
        search_strategies = [s.strip() for s in search_strategies if s.strip()]
        
        for attempt in range(max_retries + 1):
            try:
                # Use the search strategy for this attempt
                if attempt < len(search_strategies):
                    current_search = search_strategies[attempt]
                else:
                    current_search = search_strategies[0]  # Fallback to first strategy
                
                logger.info(f"🔍 Attempt {attempt + 1}: Using search term '{current_search}'")
                
                # Use folder name based on Indonesian name, but search with Latin name
                scraper = FishImageScraper(folder_species_name, min_images, self.output_base_dir, nama_latin)
                
                # Override the search term for this specific scraper instance
                scraper.current_search_term = current_search
                
                downloaded = scraper.run_scraping()
                
                result = {
                    'species_indonesia': species_name,
                    'species_english': row['species_english'],
                    'search_keyword_used': current_search,
                    'target_images': min_images,
                    'downloaded_images': downloaded,
                    'success_rate': (downloaded / min_images) * 100,
                    'status': 'SUCCESS' if downloaded >= min_images else 'PARTIAL',
                    'directory': scraper.species_dir,
                    'attempt': attempt + 1
                }
                
                # ✅ Jika berhasil mencapai target, langsung return
                if downloaded >= min_images:
                    logger.info(f"✅ SUCCESS! Got {downloaded}/{min_images} images for {species_name}")
                    return result
                
                # ⚠️ Jika belum berhasil dan masih ada attempt, lanjut ke attempt berikutnya
                if attempt < max_retries:
                    logger.info(f"⚠️ Got only {downloaded}/{min_images} images, trying next strategy...")
                else:
                    # ❌ Sudah max retries, return hasil terbaik yang didapat
                    logger.warning(f"❌ Max retries reached. Final result: {downloaded}/{min_images} images")
                    return result
                        
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for {species_name}: {e}")
                if attempt == max_retries:
                    return {
                        'species_indonesia': species_name,
                        'species_english': row['species_english'],
                        'search_keyword_used': current_search if 'current_search' in locals() else 'unknown',
                        'target_images': min_images,
                        'downloaded_images': 0,
                        'success_rate': 0,
                        'status': 'FAILED',
                        'directory': '',
                        'attempt': attempt + 1,
                        'error': str(e)
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
    
    # Output directory
    output_dir = input("Output directory (enter untuk 'fish_images'): ").strip()
    if not output_dir:
        output_dir = "fish_images"
    
    print(f"\n🎯 BATCH SCRAPING SETUP:")
    print(f"📁 Database: {csv_file}")
    print(f"🏷️ Priority: {priority_filter or 'ALL'}")
    print(f"📊 Max species: {max_species or 'ALL'}")
    print(f"📂 Output: {output_dir}")
    
    confirm = input("\nStart batch scraping? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Batch scraping cancelled")
        return
    
    # Start batch scraping
    batch_scraper = BatchFishScraper(csv_file, output_dir)
    batch_scraper.run_batch_scraping(
        max_species=max_species,
        priority_filter=priority_filter
    )

def main():
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
    main()