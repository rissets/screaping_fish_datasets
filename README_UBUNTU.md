# Fish Image Scraper - Ubuntu Server Setup Guide

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)
```bash
# Clone repository
git clone https://github.com/rissets/screaping_fish_datasets.git
cd scraping_fish

# Run deployment script
chmod +x deploy_ubuntu.sh
./deploy_ubuntu.sh
```

### Option 2: Docker Deployment (Production)
```bash
# Build and run with Docker
docker-compose up --build

# Or run interactively
docker-compose run --rm fish-scraper
```

### Option 3: Manual Setup
```bash
# Run Ubuntu setup script
chmod +x setup_ubuntu.sh
./setup_ubuntu.sh

# Activate environment
source venv/bin/activate

# Run scraper
python scraping_ubuntu.py
```

## 📋 System Requirements

### Minimum Requirements
- Ubuntu 18.04+ (20.04 or 22.04 recommended)
- 2GB RAM
- 10GB free disk space
- Internet connection

### Recommended for Production
- Ubuntu 22.04 LTS
- 4GB+ RAM
- 50GB+ SSD storage
- Dedicated server or VPS

## 🛠️ Installation Methods

### Method 1: Docker (Easiest)

#### Prerequisites
```bash
# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Log out and back in
```

#### Usage
```bash
# Interactive mode
docker-compose run --rm fish-scraper

# Background service
docker-compose up -d

# View logs
docker-compose logs -f fish-scraper

# Stop service
docker-compose down
```

### Method 2: Virtual Environment

#### Installation
```bash
# System dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git curl wget

# Clone and setup
git clone https://github.com/rissets/screaping_fish_datasets.git
cd scraping_fish
chmod +x setup_ubuntu.sh
./setup_ubuntu.sh
```

#### Usage
```bash
# Activate environment
source venv/bin/activate

# Interactive mode
python scraping_ubuntu.py

# Headless mode (for SSH/no GUI)
./run_headless.sh

# Batch mode
./run_batch.sh fish_scraping_top50.csv 10 HIGH
```

### Method 3: System Service

#### Installation
```bash
# Setup first
./setup_ubuntu.sh

# Install as service
sudo cp fish_scraper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable fish_scraper.service
```

#### Management
```bash
# Start service
sudo systemctl start fish_scraper.service

# Check status
sudo systemctl status fish_scraper.service

# View logs
sudo journalctl -u fish_scraper.service -f

# Stop service
sudo systemctl stop fish_scraper.service
```

## 🖥️ Headless Operation

### Using Xvfb (X Virtual Framebuffer)
```bash
# Start virtual display
Xvfb :99 -ac -screen 0 1280x1024x16 &
export DISPLAY=:99

# Run scraper
python scraping_ubuntu.py
```

### Using the headless runner
```bash
# Simple headless execution
./run_headless.sh
```

### Docker headless (automatic)
```bash
# Docker handles headless setup automatically
docker-compose run --rm fish-scraper
```

## 📊 Monitoring

### Built-in Monitor
```bash
# Single report
python monitor.py

# Continuous monitoring
python monitor.py --continuous --interval 30

# Save reports to JSON
python monitor.py --save-reports
```

### System Monitoring
```bash
# Check running processes
ps aux | grep scraping

# Monitor resources
htop

# Check disk space
df -h

# Check memory usage
free -h
```

### Log Monitoring
```bash
# View scraper logs
tail -f logs/scraper.log

# View system logs (if using service)
sudo journalctl -u fish_scraper.service -f

# Docker logs
docker-compose logs -f fish-scraper
```

## ⚙️ Configuration

### Environment Variables
Create `.env` file:
```bash
DISPLAY=:99
CHROME_HEADLESS=1
FIREFOX_HEADLESS=1
MAX_RETRIES=3
DOWNLOAD_TIMEOUT=30
USER_AGENT="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
```

### Config File
Edit `config.ini`:
```ini
[scraping]
min_images = 100
max_retries = 3
concurrent_downloads = 2

[browser]
headless = true
window_size = 1280x1024

[paths]
output_dir = fish_images
log_dir = logs
```

## 🚨 Troubleshooting

### Common Issues

#### Chrome/ChromeDriver Issues
```bash
# Check Chrome version
google-chrome --version

# Reinstall ChromeDriver
python3 -c "from webdriver_manager.chrome import ChromeDriverManager; ChromeDriverManager().install()"

# Check display
echo $DISPLAY
xset -display :99 -q  # Should not error
```

#### Display Issues
```bash
# Start Xvfb manually
sudo pkill Xvfb
Xvfb :99 -ac -screen 0 1280x1024x16 &
export DISPLAY=:99

# Install xvfb if missing
sudo apt install -y xvfb
```

#### Permission Issues
```bash
# Fix file permissions
chmod +x *.sh
sudo chown -R $USER:$USER .

# Fix ChromeDriver permissions
find ~/.wdm -name "chromedriver*" -exec chmod +x {} \;
```

#### Memory Issues
```bash
# Check memory usage
free -h

# Reduce concurrent downloads
# Edit scraping.py: self.max_concurrent = 1

# Add swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### Network Issues
```bash
# Test internet connectivity
curl -I https://www.google.com
curl -I https://unsplash.com
curl -I https://commons.wikimedia.org

# Check DNS
nslookup google.com

# Disable IPv6 if issues
echo 'net.ipv6.conf.all.disable_ipv6 = 1' | sudo tee -a /etc/sysctl.conf
```

### Error Solutions

#### "Display not found"
```bash
export DISPLAY=:99
Xvfb :99 -ac -screen 0 1280x1024x16 &
```

#### "ChromeDriver not executable"
```bash
find ~/.wdm -name "chromedriver*" -exec chmod +x {} \;
```

#### "No module named 'selenium'"
```bash
source venv/bin/activate
pip install -r requirements.txt
```

#### "Permission denied: fish_images"
```bash
sudo chown -R $USER:$USER fish_images/
chmod -R 755 fish_images/
```

## 📈 Performance Optimization

### For Large Batch Jobs
```bash
# Use Docker with resource limits
docker-compose run --rm \
    --memory=2g \
    --cpus=2 \
    fish-scraper

# Or edit docker-compose.yml:
# deploy:
#   resources:
#     limits:
#       memory: 2G
#       cpus: '2'
```

### For Limited Resources
```bash
# Reduce concurrent operations
export MAX_CONCURRENT_DOWNLOADS=1
export DOWNLOAD_DELAY=3

# Use smaller batches
./run_batch.sh fish_scraping_top50.csv 5 HIGH
```

### For High-Performance Servers
```bash
# Increase concurrent operations
export MAX_CONCURRENT_DOWNLOADS=4
export DOWNLOAD_DELAY=0.5

# Use full dataset
./run_batch.sh fish_scraping_list_updated.csv 100 ALL
```

## 🔐 Security Considerations

### User Permissions
```bash
# Don't run as root
# Create dedicated user
sudo useradd -m -s /bin/bash fishscraper
sudo usermod -aG docker fishscraper

# Run as dedicated user
sudo -u fishscraper ./deploy_ubuntu.sh
```

### Network Security
```bash
# Use firewall if needed
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow out 80
sudo ufw allow out 443
```

### File Permissions
```bash
# Secure directories
chmod 750 fish_images/
chmod 750 logs/
chmod 640 *.csv
chmod 755 *.sh
```

## 📊 Monitoring & Alerting

### Automated Monitoring
```bash
# Setup cron job for monitoring
echo "*/5 * * * * cd /path/to/scraper && python monitor.py --save-reports" | crontab -
```

### Email Alerts (Optional)
```bash
# Install mail utilities
sudo apt install -y mailutils

# Add to cron for alerts
echo "0 */6 * * * cd /path/to/scraper && python monitor.py | mail -s 'Scraper Status' admin@example.com" | crontab -
```

### Web Dashboard (Advanced)
Consider setting up Grafana + InfluxDB for advanced monitoring.

## 🆘 Support

### Logs Location
- Application logs: `logs/scraper.log`
- System service logs: `journalctl -u fish_scraper.service`
- Docker logs: `docker-compose logs fish-scraper`

### Getting Help
1. Check logs first
2. Run monitor.py for system status
3. Test with single species first
4. Check GitHub issues
5. Create detailed bug report with logs

### Useful Commands
```bash
# System info
uname -a
lsb_release -a
free -h
df -h

# Python info
python3 --version
pip list | grep selenium

# Network info
ip addr show
ping -c 3 google.com
```