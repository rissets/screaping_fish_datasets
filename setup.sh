#!/bin/bash
# Fish Image Scraper Setup Script

echo "🐟 Fish Image Scraper Setup 🐟"
echo "================================"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install Python3 first."
    exit 1
fi

# Create virtual environment
# echo "📦 Creating virtual environment..."
# python3 -m venv fish_scraper_env

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "⬇️ Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# ChromeDriver will be automatically managed by webdriver-manager
echo "✅ ChromeDriver will be automatically downloaded when needed..."
echo "📝 Note: webdriver-manager will handle ChromeDriver installation safely"
else
    echo "⚠️ Homebrew not found. Please install ChromeDriver manually:"
    echo "   1. Download from: https://chromedriver.chromium.org/"
    echo "   2. Add to PATH"
fi

echo "✅ Setup complete!"
echo ""
echo "To use the scraper:"
echo "1. Activate virtual environment: source fish_scraper_env/bin/activate"
echo "2. Run the scraper: python3 scraping.py"
echo ""
echo "To deactivate virtual environment: deactivate"