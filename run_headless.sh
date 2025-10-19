#!/bin/bash

# Fish Image Scraper - Headless Runner
# Runs the scraper in headless mode for Ubuntu servers

echo "🐟 Fish Image Scraper - Headless Mode 🐟"
echo "========================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Please run setup_ubuntu.sh first"
    exit 1
fi

# Set environment for headless operation
export DISPLAY=:99
export CHROME_HEADLESS=1
export FIREFOX_HEADLESS=1

# Start Xvfb (virtual display) for headless operation
echo "🖥️ Starting virtual display..."
Xvfb :99 -ac -screen 0 1280x1024x16 &
XVFB_PID=$!

# Wait a moment for Xvfb to start
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

# Check if scraping.py exists
if [ ! -f "scraping.py" ]; then
    echo "❌ scraping.py not found!"
    kill $XVFB_PID 2>/dev/null
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Run the scraper
echo "🚀 Starting Fish Image Scraper in headless mode..."
echo "   Log file: logs/headless_$(date +%Y%m%d_%H%M%S).log"

# Run scraper and capture output
python scraping.py 2>&1 | tee "logs/headless_$(date +%Y%m%d_%H%M%S).log"

# Capture exit code
SCRAPER_EXIT_CODE=$?

# Clean up Xvfb process
echo "🧹 Cleaning up virtual display..."
kill $XVFB_PID 2>/dev/null

# Wait for process to terminate
sleep 1

if [ $SCRAPER_EXIT_CODE -eq 0 ]; then
    echo "✅ Headless scraping completed successfully"
else
    echo "❌ Headless scraping completed with errors (exit code: $SCRAPER_EXIT_CODE)"
fi

echo "📁 Check fish_images/ directory for downloaded images"
echo "📝 Check logs/ directory for detailed logs"

exit $SCRAPER_EXIT_CODE