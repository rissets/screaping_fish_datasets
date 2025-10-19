#!/bin/bash

# Fish Image Scraper Setup for Ubuntu Server
# This script installs all dependencies and configures the environment

echo "🐟 Fish Image Scraper Setup for Ubuntu Server 🐟"
echo "=================================================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "❌ This script should not be run as root"
   echo "   Run as regular user, sudo will be used when needed"
   exit 1
fi

# Update system packages
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install system dependencies
echo "🔧 Installing system dependencies..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    curl \
    wget \
    unzip \
    xvfb \
    xauth \
    libnss3-dev \
    libgconf-2-4 \
    libxss1 \
    libappindicator1 \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libgtk-3-0 \
    libxkbcommon0 \
    git

# Install Chrome (needed for ChromeDriver)
echo "🌐 Installing Google Chrome..."
if ! command -v google-chrome &> /dev/null; then
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
    sudo apt update
    sudo apt install -y google-chrome-stable
    echo "✅ Google Chrome installed"
else
    echo "✅ Google Chrome already installed"
fi

# Install Firefox (alternative browser)
echo "🦊 Installing Firefox..."
sudo apt install -y firefox

# Create virtual environment
echo "🐍 Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment and install Python packages
echo "📚 Installing Python packages..."
source venv/bin/activate
pip install --upgrade pip

# Install packages from requirements.txt
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Python packages installed from requirements.txt"
else
    echo "⚠️ requirements.txt not found, installing manually..."
    pip install requests beautifulsoup4 selenium Pillow tqdm webdriver-manager lxml pandas
fi

# Install additional packages for headless operation
pip install pyvirtualdisplay

# Set up ChromeDriver permissions (Ubuntu specific)
echo "🔐 Setting up ChromeDriver permissions..."
CHROME_VERSION=$(google-chrome --version | grep -oE "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}")
echo "Chrome version: $CHROME_VERSION"

# Download and setup ChromeDriver if needed
echo "🚗 Setting up ChromeDriver..."
python3 -c "
from webdriver_manager.chrome import ChromeDriverManager
import os
import stat
try:
    driver_path = ChromeDriverManager().install()
    print(f'ChromeDriver installed at: {driver_path}')
    # Make sure it's executable
    os.chmod(driver_path, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
    print('✅ ChromeDriver permissions set')
except Exception as e:
    print(f'❌ ChromeDriver setup failed: {e}')
"

# Create systemd service file for running as daemon (optional)
echo "⚙️ Creating systemd service template..."
cat > fish_scraper.service << EOF
[Unit]
Description=Fish Image Scraper
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=DISPLAY=:99
ExecStartPre=/usr/bin/Xvfb :99 -ac -screen 0 1280x1024x16 &
ExecStart=$(pwd)/venv/bin/python $(pwd)/scraping.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "📄 Service file created: fish_scraper.service"
echo "   To install: sudo cp fish_scraper.service /etc/systemd/system/"
echo "   To enable:  sudo systemctl enable fish_scraper.service"
echo "   To start:   sudo systemctl start fish_scraper.service"

# Create startup script for headless operation
echo "🖥️ Creating headless startup script..."
cat > run_headless.sh << 'EOF'
#!/bin/bash

# Start Xvfb (virtual display) for headless operation
export DISPLAY=:99
Xvfb :99 -ac -screen 0 1280x1024x16 &
XVFB_PID=$!

# Activate virtual environment
source venv/bin/activate

# Run the scraper
python scraping.py

# Clean up
kill $XVFB_PID 2>/dev/null
EOF

chmod +x run_headless.sh
echo "✅ Headless runner created: run_headless.sh"

# Create batch runner script
echo "📦 Creating batch runner script..."
cat > run_batch.sh << 'EOF'
#!/bin/bash

# Batch runner for Fish Image Scraper
# Usage: ./run_batch.sh [csv_file] [max_species] [priority]

export DISPLAY=:99
Xvfb :99 -ac -screen 0 1280x1024x16 &
XVFB_PID=$!

source venv/bin/activate

CSV_FILE=${1:-"fish_scraping_list_updated.csv"}
MAX_SPECIES=${2:-10}
PRIORITY=${3:-"HIGH"}

echo "🐟 Running batch scraper..."
echo "📁 CSV File: $CSV_FILE"
echo "📊 Max Species: $MAX_SPECIES" 
echo "🏷️ Priority: $PRIORITY"

python3 -c "
from scraping import BatchFishScraper
import sys

try:
    scraper = BatchFishScraper('$CSV_FILE')
    priority_filter = '$PRIORITY' if '$PRIORITY' != 'ALL' else None
    max_species = int('$MAX_SPECIES') if '$MAX_SPECIES'.isdigit() else None
    
    scraper.run_batch_scraping(
        max_species=max_species,
        priority_filter=priority_filter
    )
except Exception as e:
    print(f'❌ Batch scraping failed: {e}')
    sys.exit(1)
"

kill $XVFB_PID 2>/dev/null
echo "✅ Batch scraping completed"
EOF

chmod +x run_batch.sh
echo "✅ Batch runner created: run_batch.sh"

# Create environment configuration
echo "🔧 Creating environment configuration..."
cat > .env << EOF
# Fish Scraper Environment Configuration
DISPLAY=:99
CHROME_HEADLESS=1
FIREFOX_HEADLESS=1
MAX_RETRIES=3
DOWNLOAD_TIMEOUT=30
USER_AGENT="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
EOF

# Create log directory
mkdir -p logs
echo "📝 Log directory created: logs/"

# Test the setup
echo "🧪 Testing setup..."
source venv/bin/activate

echo "Testing Python imports..."
python3 -c "
import requests
import selenium
import PIL
from bs4 import BeautifulSoup
import pandas as pd
print('✅ All Python packages imported successfully')
"

echo "Testing ChromeDriver..."
python3 -c "
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

try:
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.get('https://www.google.com')
    print('✅ ChromeDriver test successful')
    driver.quit()
except Exception as e:
    print(f'⚠️ ChromeDriver test failed: {e}')
    print('   You may need to run with Xvfb for headless mode')
"

# Create README for Ubuntu setup
echo "📖 Creating Ubuntu setup documentation..."
cat > README_UBUNTU.md << 'EOF'
# Fish Image Scraper - Ubuntu Server Setup

## Installation

1. Run the setup script:
```bash
chmod +x setup_ubuntu.sh
./setup_ubuntu.sh
```

## Usage

### Interactive Mode
```bash
# Activate virtual environment
source venv/bin/activate

# Run interactively
python scraping.py
```

### Headless Mode (for servers without GUI)
```bash
# Run with virtual display
./run_headless.sh
```

### Batch Mode
```bash
# Run batch scraping
./run_batch.sh [csv_file] [max_species] [priority]

# Examples:
./run_batch.sh fish_scraping_top50.csv 10 HIGH
./run_batch.sh fish_scraping_list_updated.csv 50 ALL
```

### As System Service
```bash
# Install service
sudo cp fish_scraper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable fish_scraper.service

# Start service
sudo systemctl start fish_scraper.service

# Check status
sudo systemctl status fish_scraper.service

# View logs
sudo journalctl -u fish_scraper.service -f
```

## Environment Variables

Edit `.env` file to customize:
- `DISPLAY`: X11 display for headless mode
- `CHROME_HEADLESS`: Enable Chrome headless mode
- `MAX_RETRIES`: Maximum retry attempts
- `DOWNLOAD_TIMEOUT`: Download timeout in seconds

## Troubleshooting

### ChromeDriver Issues
```bash
# Manual ChromeDriver install
python3 -c "from webdriver_manager.chrome import ChromeDriverManager; ChromeDriverManager().install()"
```

### Display Issues (Headless)
```bash
# Start Xvfb manually
Xvfb :99 -ac -screen 0 1280x1024x16 &
export DISPLAY=:99
```

### Permission Issues
```bash
# Fix permissions
chmod +x *.sh
sudo chown -R $USER:$USER fish_images/
```

### Memory Issues
```bash
# Monitor memory usage
htop

# Reduce concurrent downloads
# Edit scraping.py and reduce min_images or add delays
```

## File Structure
```
fish_scraping/
├── scraping.py              # Main scraper
├── setup_ubuntu.sh          # Ubuntu setup script
├── run_headless.sh          # Headless runner
├── run_batch.sh             # Batch runner
├── fish_scraper.service     # Systemd service
├── requirements.txt         # Python dependencies
├── .env                     # Environment config
├── fish_scraping_list_updated.csv  # Fish database
├── fish_scraping_top50.csv         # Top 50 species
├── venv/                    # Python virtual environment
├── fish_images/            # Downloaded images
└── logs/                   # Log files
```
EOF

echo ""
echo "🎉 Ubuntu Server Setup Complete!"
echo "=================================================="
echo "✅ System packages installed"
echo "✅ Python virtual environment created"
echo "✅ Python packages installed"
echo "✅ ChromeDriver configured"
echo "✅ Headless operation scripts created"
echo "✅ Batch runner created"
echo "✅ Service file template created"
echo "✅ Documentation created"
echo ""
echo "📖 Read README_UBUNTU.md for detailed usage instructions"
echo ""
echo "🚀 Quick Start:"
echo "   Interactive: python scraping.py"
echo "   Headless:    ./run_headless.sh"
echo "   Batch:       ./run_batch.sh fish_scraping_top50.csv 5 HIGH"
echo ""
echo "🔧 For production servers, consider installing as systemd service"
echo "   See README_UBUNTU.md for instructions"