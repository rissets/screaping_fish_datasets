#!/bin/bash

# Fish Image Scraper - Ubuntu Server Deployment Script
# This script helps deploy the scraper on Ubuntu servers

set -e  # Exit on any error

echo "🐟 Fish Image Scraper - Ubuntu Server Deployment 🐟"
echo "===================================================="

# Check if Docker is available
check_docker() {
    if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
        echo "✅ Docker and Docker Compose found"
        return 0
    else
        echo "❌ Docker or Docker Compose not found"
        return 1
    fi
}

# Install Docker if needed
install_docker() {
    echo "📦 Installing Docker..."
    
    # Remove old versions
    sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    # Update package index
    sudo apt-get update
    
    # Install dependencies
    sudo apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # Add Docker's official GPG key
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Set up repository
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker Engine
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    # Install Docker Compose (standalone)
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    # Add user to docker group
    sudo usermod -aG docker $USER
    
    echo "✅ Docker installed successfully"
    echo "⚠️  Please log out and back in for Docker group membership to take effect"
}

# Deploy using Docker
deploy_docker() {
    echo "🐳 Deploying with Docker..."
    
    # Build and run
    docker-compose build
    
    echo "✅ Docker image built successfully"
    echo ""
    echo "🚀 Deployment options:"
    echo "1. Run interactively:     docker-compose run --rm fish-scraper"
    echo "2. Run in background:     docker-compose up -d"
    echo "3. View logs:             docker-compose logs -f fish-scraper"
    echo "4. Stop service:          docker-compose down"
    echo ""
    
    read -p "Start the scraper now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose run --rm fish-scraper
    fi
}

# Deploy using virtual environment
deploy_venv() {
    echo "🐍 Deploying with Python virtual environment..."
    
    # Run the Ubuntu setup script
    if [ -f "setup_ubuntu.sh" ]; then
        ./setup_ubuntu.sh
    else
        echo "❌ setup_ubuntu.sh not found"
        exit 1
    fi
    
    echo "✅ Virtual environment deployment complete"
    echo ""
    echo "🚀 Usage:"
    echo "1. Interactive mode:      python3 scraping_ubuntu.py"
    echo "2. Headless mode:         ./run_headless.sh"
    echo "3. Batch mode:            ./run_batch.sh"
    echo ""
}

# Deploy as systemd service
deploy_service() {
    echo "⚙️ Deploying as systemd service..."
    
    # Ensure setup is complete
    if [ ! -d "venv" ]; then
        echo "Running setup first..."
        ./setup_ubuntu.sh
    fi
    
    # Install service
    sudo cp fish_scraper.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable fish_scraper.service
    
    echo "✅ Service installed"
    echo ""
    echo "🚀 Service management:"
    echo "1. Start:    sudo systemctl start fish_scraper"
    echo "2. Stop:     sudo systemctl stop fish_scraper"
    echo "3. Status:   sudo systemctl status fish_scraper"
    echo "4. Logs:     sudo journalctl -u fish_scraper -f"
    echo ""
    
    read -p "Start the service now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo systemctl start fish_scraper.service
        sudo systemctl status fish_scraper.service
    fi
}

# Main deployment menu
main() {
    echo "Select deployment method:"
    echo "1. Docker (Recommended for production)"
    echo "2. Virtual Environment (Manual setup)"
    echo "3. Systemd Service (Background service)"
    echo "4. Exit"
    
    while true; do
        read -p "Choice (1-4): " choice
        case $choice in
            1)
                if check_docker; then
                    deploy_docker
                else
                    read -p "Install Docker? (y/n): " -n 1 -r
                    echo
                    if [[ $REPLY =~ ^[Yy]$ ]]; then
                        install_docker
                        echo "Please log out and back in, then run this script again"
                        exit 0
                    fi
                fi
                break
                ;;
            2)
                deploy_venv
                break
                ;;
            3)
                deploy_service
                break
                ;;
            4)
                echo "Goodbye!"
                exit 0
                ;;
            *)
                echo "❌ Invalid choice. Please select 1-4."
                ;;
        esac
    done
}

# Check if running on Ubuntu
if [[ ! $(lsb_release -si 2>/dev/null) == "Ubuntu" ]]; then
    echo "⚠️  Warning: This script is designed for Ubuntu. It may not work on other distributions."
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

# Check if files exist
required_files=("scraping.py" "requirements.txt")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Required file not found: $file"
        echo "Please run this script from the project directory"
        exit 1
    fi
done

# Run main function
main

echo ""
echo "🎉 Deployment complete!"
echo "📖 Check README_UBUNTU.md for detailed usage instructions"