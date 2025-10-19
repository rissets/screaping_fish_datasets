# 🐟 Fish Image Scraper

Aplikasi Python untuk scraping gambar ikan dari berbagai sumber dengan fitur interaktif dan struktur yang terorganisir.

## ✨ Fitur

- **Interaktif**: Input species ikan dan jumlah minimum gambar yang diinginkan
- **Multi-source scraping**: Google Images, Bing Images, dan FishBase
- **Validasi gambar**: Hanya download JPG/PNG dengan ukuran minimum
- **Struktur terorganisir**: Gambar disimpan dalam folder berdasarkan species
- **Retry mechanism**: Tidak berhenti sampai mendapat jumlah minimum gambar
- **Progress tracking**: Menampilkan progress bar dan log detail
- **Error handling**: Robust error handling untuk stabilitas
- **Safe scraping**: Rate limiting dan random delays

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Jalankan script setup otomatis
./setup.sh
```

Atau manual:

```bash
# Buat virtual environment
python3 -m venv fish_scraper_env
source fish_scraper_env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install ChromeDriver (untuk macOS)
brew install chromedriver
```

### 2. Jalankan Scraper

```bash
# Aktifkan virtual environment
source fish_scraper_env/bin/activate

# Jalankan scraper
python3 scraping.py
```

## 📖 Cara Penggunaan

1. **Masukkan species ikan**:
   ```
   Enter fish species (e.g., 'nemo clownfish', 'goldfish'): goldfish
   ```

2. **Masukkan jumlah minimum gambar**:
   ```
   Enter minimum number of images to scrape: 50
   ```

3. **Pilih output directory** (opsional):
   ```
   Enter output directory (press Enter for default 'fish_images'): my_fish_collection
   ```

4. **Konfirmasi dan mulai scraping**:
   ```
   🎯 Target: 50 images of 'goldfish'
   📁 Output: my_fish_collection/goldfish
   
   Proceed with scraping? (y/n): y
   ```

## 📁 Struktur Output

```
fish_images/
├── goldfish/
│   ├── goldfish_0001.jpg
│   ├── goldfish_0002.jpg
│   └── ...
├── clownfish/
│   ├── clownfish_0001.jpg
│   ├── clownfish_0002.jpg
│   └── ...
└── ...
```

## 🛡️ Fitur Keamanan

- **User-Agent rotation**: Menggunakan user-agent browser real
- **Rate limiting**: Delay random antar request
- **Content validation**: Validasi tipe file dan ukuran gambar
- **Error recovery**: Automatic retry untuk request yang gagal
- **Headless browser**: Selenium berjalan tanpa UI

## 📊 Sumber Data

1. **Google Images**: Primary source dengan Selenium
2. **Bing Images**: Secondary source dengan requests
3. **FishBase**: Specialized fish database untuk akurasi tinggi

## ⚙️ Konfigurasi

### Mengubah Minimum Size Gambar

Edit di `scraping.py` line ~75:

```python
if img.width < 100 or img.height < 100:  # Ubah nilai ini
```

### Menambah Delay

Edit random delay di berbagai fungsi:

```python
time.sleep(random.uniform(1, 2))  # Ubah range ini
```

## 🔧 Troubleshooting

### ChromeDriver Issues

```bash
# Update ChromeDriver
brew upgrade chromedriver

# Atau download manual dari:
# https://chromedriver.chromium.org/
```

### Permission Issues

```bash
# Berikan permission untuk ChromeDriver
sudo xattr -d com.apple.quarantine /usr/local/bin/chromedriver
```

### Memory Issues

Untuk scraping jumlah besar:

```python
# Kurangi concurrent requests di kode
# atau restart script secara berkala
```

## 📝 Log Files

Script akan menghasilkan log dengan format:

```
2024-10-19 10:30:15,123 - INFO - Starting to scrape images for: goldfish
2024-10-19 10:30:16,234 - INFO - Downloaded: fish_images/goldfish/goldfish_0001.jpg
2024-10-19 10:30:17,345 - WARNING - Image too small: 50x30
2024-10-19 10:30:18,456 - ERROR - Download failed for http://example.com/img.jpg: Timeout
```

## 🤝 Contributing

1. Fork repository
2. Buat feature branch
3. Commit changes
4. Push ke branch
5. Create Pull Request

## 📄 License

MIT License - silakan gunakan dan modifikasi sesuai kebutuhan.

## 🆘 Support

Jika mengalami masalah:

1. Check log output untuk error details
2. Pastikan semua dependencies terinstall
3. Verify ChromeDriver compatibility
4. Check internet connection
5. Try dengan species name yang lebih spesifik

## 🔄 Updates

Untuk update ke versi terbaru:

```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

---

**Happy Fish Scraping! 🐟🎣**