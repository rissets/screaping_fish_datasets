#!/usr/bin/env python3
"""
Fish Scraper Monitor - Ubuntu Server
Monitors scraping progress and system resources
"""

import psutil
import time
import os
import json
import logging
from datetime import datetime, timedelta
import argparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ScrapingMonitor:
    def __init__(self, log_file='logs/scraper.log', output_dir='fish_images'):
        self.log_file = log_file
        self.output_dir = output_dir
        self.start_time = datetime.now()
        
    def get_system_stats(self):
        """Get current system statistics"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'load_average': os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0
        }
    
    def get_scraping_progress(self):
        """Monitor scraping progress from directories"""
        progress = {
            'total_species': 0,
            'completed_species': 0,
            'total_images': 0,
            'species_list': []
        }
        
        try:
            if os.path.exists(self.output_dir):
                species_dirs = [d for d in os.listdir(self.output_dir) 
                              if os.path.isdir(os.path.join(self.output_dir, d))]
                
                progress['total_species'] = len(species_dirs)
                
                for species_dir in species_dirs:
                    species_path = os.path.join(self.output_dir, species_dir)
                    images = [f for f in os.listdir(species_path) 
                             if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                    
                    species_info = {
                        'name': species_dir,
                        'image_count': len(images),
                        'completed': len(images) >= 100  # Assuming 100 is the target
                    }
                    
                    if species_info['completed']:
                        progress['completed_species'] += 1
                    
                    progress['total_images'] += len(images)
                    progress['species_list'].append(species_info)
        
        except Exception as e:
            logger.error(f"Error getting progress: {e}")
        
        return progress
    
    def parse_log_stats(self):
        """Parse statistics from log file"""
        stats = {
            'errors': 0,
            'warnings': 0,
            'downloads': 0,
            'last_activity': None
        }
        
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    lines = f.readlines()
                    
                for line in lines:
                    if 'ERROR' in line:
                        stats['errors'] += 1
                    elif 'WARNING' in line:
                        stats['warnings'] += 1
                    elif 'Downloaded:' in line:
                        stats['downloads'] += 1
                        # Extract timestamp for last activity
                        try:
                            timestamp = line.split(' - ')[0]
                            stats['last_activity'] = timestamp
                        except:
                            pass
        
        except Exception as e:
            logger.error(f"Error parsing logs: {e}")
        
        return stats
    
    def get_running_processes(self):
        """Get scraper-related running processes"""
        processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_percent', 'cpu_percent']):
                try:
                    if any('scraping' in str(cmd).lower() for cmd in proc.info['cmdline'] or []):
                        processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'memory_percent': proc.info['memory_percent'],
                            'cpu_percent': proc.info['cpu_percent']
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        
        except Exception as e:
            logger.error(f"Error getting processes: {e}")
        
        return processes
    
    def generate_report(self):
        """Generate comprehensive monitoring report"""
        system_stats = self.get_system_stats()
        progress = self.get_scraping_progress()
        log_stats = self.parse_log_stats()
        processes = self.get_running_processes()
        
        runtime = datetime.now() - self.start_time
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'runtime_seconds': runtime.total_seconds(),
            'system': system_stats,
            'progress': progress,
            'logs': log_stats,
            'processes': processes,
            'status': self.determine_status(system_stats, progress, processes)
        }
        
        return report
    
    def determine_status(self, system_stats, progress, processes):
        """Determine overall scraping status"""
        if processes:
            if system_stats['cpu_percent'] > 80 or system_stats['memory_percent'] > 90:
                return 'OVERLOADED'
            else:
                return 'RUNNING'
        elif progress['total_species'] > 0:
            completion_rate = progress['completed_species'] / progress['total_species']
            if completion_rate >= 1.0:
                return 'COMPLETED'
            else:
                return 'PAUSED'
        else:
            return 'IDLE'
    
    def print_report(self, report):
        """Print formatted report to console"""
        print("\n" + "="*60)
        print("🐟 FISH SCRAPER MONITORING REPORT")
        print("="*60)
        print(f"⏰ Time: {report['timestamp']}")
        print(f"⌛ Runtime: {timedelta(seconds=int(report['runtime_seconds']))}")
        print(f"📊 Status: {report['status']}")
        
        print(f"\n🖥️  SYSTEM RESOURCES:")
        print(f"   CPU: {report['system']['cpu_percent']:.1f}%")
        print(f"   Memory: {report['system']['memory_percent']:.1f}%")
        print(f"   Disk: {report['system']['disk_usage']:.1f}%")
        print(f"   Load: {report['system']['load_average']:.2f}")
        
        print(f"\n📈 SCRAPING PROGRESS:")
        print(f"   Total Species: {report['progress']['total_species']}")
        print(f"   Completed: {report['progress']['completed_species']}")
        print(f"   Total Images: {report['progress']['total_images']}")
        
        if report['progress']['total_species'] > 0:
            completion_rate = report['progress']['completed_species'] / report['progress']['total_species'] * 100
            print(f"   Completion: {completion_rate:.1f}%")
        
        print(f"\n📝 LOG STATISTICS:")
        print(f"   Downloads: {report['logs']['downloads']}")
        print(f"   Warnings: {report['logs']['warnings']}")
        print(f"   Errors: {report['logs']['errors']}")
        print(f"   Last Activity: {report['logs']['last_activity'] or 'N/A'}")
        
        if report['processes']:
            print(f"\n🔄 RUNNING PROCESSES:")
            for proc in report['processes']:
                print(f"   PID {proc['pid']}: {proc['name']} (CPU: {proc['cpu_percent']:.1f}%, MEM: {proc['memory_percent']:.1f}%)")
        else:
            print(f"\n🔄 PROCESSES: No scraper processes running")
        
        # Top 5 species by image count
        if report['progress']['species_list']:
            top_species = sorted(report['progress']['species_list'], 
                               key=lambda x: x['image_count'], reverse=True)[:5]
            print(f"\n🏆 TOP SPECIES BY IMAGES:")
            for i, species in enumerate(top_species, 1):
                status = "✅" if species['completed'] else "🔄"
                print(f"   {i}. {species['name']}: {species['image_count']} images {status}")
        
        print("="*60)
    
    def save_report(self, report, filename=None):
        """Save report to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs/monitor_report_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report saved to {filename}")

def main():
    parser = argparse.ArgumentParser(description='Fish Scraper Monitor')
    parser.add_argument('--log-file', default='logs/scraper.log', 
                       help='Path to scraper log file')
    parser.add_argument('--output-dir', default='fish_images', 
                       help='Scraper output directory')
    parser.add_argument('--interval', type=int, default=60, 
                       help='Monitoring interval in seconds')
    parser.add_argument('--save-reports', action='store_true', 
                       help='Save reports to JSON files')
    parser.add_argument('--continuous', action='store_true', 
                       help='Run continuously')
    
    args = parser.parse_args()
    
    monitor = ScrapingMonitor(args.log_file, args.output_dir)
    
    try:
        if args.continuous:
            print("🔍 Starting continuous monitoring...")
            print("   Press Ctrl+C to stop")
            
            while True:
                report = monitor.generate_report()
                monitor.print_report(report)
                
                if args.save_reports:
                    monitor.save_report(report)
                
                time.sleep(args.interval)
        else:
            # Single report
            report = monitor.generate_report()
            monitor.print_report(report)
            
            if args.save_reports:
                monitor.save_report(report)
    
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Monitor error: {e}")

if __name__ == "__main__":
    main()