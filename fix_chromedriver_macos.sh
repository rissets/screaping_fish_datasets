#!/bin/bash

echo "🔧 Fixing ChromeDriver security issues on macOS..."

# Find ChromeDriver location
CHROMEDRIVER_PATH=$(which chromedriver 2>/dev/null)

if [ -z "$CHROMEDRIVER_PATH" ]; then
    echo "🔍 ChromeDriver not found in PATH, checking webdriver-manager cache..."
    
    # Check common webdriver-manager locations
    POSSIBLE_PATHS=(
        "$HOME/.wdm/drivers/chromedriver"
        "$HOME/.cache/selenium/chromedriver"
        "/usr/local/bin/chromedriver"
        "./chromedriver"
    )
    
    for path in "${POSSIBLE_PATHS[@]}"; do
        if find "$path" -name "chromedriver*" -type f 2>/dev/null | head -1; then
            CHROMEDRIVER_PATH=$(find "$path" -name "chromedriver*" -type f 2>/dev/null | head -1)
            break
        fi
    done
fi

if [ -n "$CHROMEDRIVER_PATH" ]; then
    echo "📍 Found ChromeDriver at: $CHROMEDRIVER_PATH"
    echo "🔓 Removing quarantine attribute..."
    
    # Remove quarantine attribute
    sudo xattr -r -d com.apple.quarantine "$CHROMEDRIVER_PATH" 2>/dev/null || true
    
    # Make executable
    chmod +x "$CHROMEDRIVER_PATH"
    
    echo "✅ ChromeDriver quarantine removed!"
    echo "🧪 Testing ChromeDriver..."
    
    # Test ChromeDriver
    if "$CHROMEDRIVER_PATH" --version 2>/dev/null; then
        echo "✅ ChromeDriver is working!"
    else
        echo "❌ ChromeDriver test failed"
        echo "💡 Try allowing ChromeDriver in System Preferences > Security & Privacy"
    fi
else
    echo "❌ ChromeDriver not found"
    echo "💡 Installing ChromeDriver using webdriver-manager..."
    
    python3 -c "
from webdriver_manager.chrome import ChromeDriverManager
import os
path = ChromeDriverManager().install()
print(f'ChromeDriver installed at: {path}')
os.system(f'sudo xattr -r -d com.apple.quarantine \"{path}\" 2>/dev/null || true')
os.system(f'chmod +x \"{path}\"')
print('ChromeDriver quarantine removed!')
"
fi

echo ""
echo "🍎 macOS Security Tips:"
echo "1. If you still get security warnings, go to:"
echo "   System Preferences > Security & Privacy > General"
echo "2. Click 'Allow Anyway' when you see ChromeDriver blocked"
echo "3. Alternatively, use Safari WebDriver (built-in, more secure)"
echo ""