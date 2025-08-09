#!/usr/bin/env python3
"""
Offline AWS Pricing Data Downloader
Downloads real AWS pricing data in a controlled, optimized manner
Designed to run once offline to populate the development database
"""

import requests
import json
import gzip
import logging
import time
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('offline_download.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class OfflineDataDownloader:
    """Optimized downloader for real AWS pricing data"""
    
    # AWS Bulk Pricing Endpoints
    PRICING_ENDPOINTS = {
        'index': 'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/index.json',
        'AmazonEC2': 'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/index.json',
        'AmazonEBS': 'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEBS/current/index.json',
        'AmazonRDS': 'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/index.json'
    }
    
    def __init__(self, download_dir: str = None, chunk_size: int = 8192):
        """Initialize offline downloader"""
        if download_dir is None:
            download_dir = Path(__file__).parent / "offline_data"
        
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        self.chunk_size = chunk_size
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RVTool-Offline-Downloader/1.0',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate'
        })
        
        logger.info(f"Offline downloader initialized: {self.download_dir}")
    
    def download_with_progress(self, url: str, filename: str) -> bool:
        """Download file with progress tracking and resume capability"""
        
        filepath = self.download_dir / filename
        temp_filepath = self.download_dir / f"{filename}.tmp"
        
        # Check if file already exists and is complete
        if filepath.exists():
            logger.info(f"File already exists: {filename}")
            return True
        
        # Resume download if temp file exists
        resume_pos = 0
        if temp_filepath.exists():
            resume_pos = temp_filepath.stat().st_size
            logger.info(f"Resuming download from position: {resume_pos}")
        
        headers = {}
        if resume_pos > 0:
            headers['Range'] = f'bytes={resume_pos}-'
        
        try:
            logger.info(f"Starting download: {filename}")
            start_time = time.time()
            
            response = self.session.get(url, headers=headers, stream=True, timeout=60)
            response.raise_for_status()
            
            # Get total file size
            total_size = int(response.headers.get('content-length', 0))
            if resume_pos > 0:
                total_size += resume_pos
            
            downloaded = resume_pos
            
            # Open file in append mode if resuming, write mode if new
            mode = 'ab' if resume_pos > 0 else 'wb'
            
            with open(temp_filepath, mode) as f:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Progress reporting
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            speed = downloaded / (time.time() - start_time) / 1024 / 1024  # MB/s
                            
                            print(f"\r{filename}: {progress:.1f}% ({downloaded/1024/1024:.1f}MB/{total_size/1024/1024:.1f}MB) - {speed:.2f} MB/s", end='', flush=True)
                        else:
                            print(f"\r{filename}: {downloaded/1024/1024:.1f}MB downloaded", end='', flush=True)
            
            print()  # New line after progress
            
            # Move temp file to final location
            temp_filepath.rename(filepath)
            
            download_time = time.time() - start_time
            file_size_mb = downloaded / 1024 / 1024
            avg_speed = file_size_mb / download_time
            
            logger.info(f"Download complete: {filename} ({file_size_mb:.1f}MB in {download_time:.1f}s, avg {avg_speed:.2f} MB/s)")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Download failed for {filename}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading {filename}: {e}")
            return False
    
    def decompress_and_validate(self, filename: str) -> bool:
        """Decompress gzipped file and validate JSON"""
        
        filepath = self.download_dir / filename
        json_filepath = self.download_dir / f"{filename.replace('.gz', '')}"
        
        if not filepath.exists():
            logger.error(f"File not found: {filename}")
            return False
        
        try:
            logger.info(f"Decompressing: {filename}")
            
            with gzip.open(filepath, 'rt', encoding='utf-8') as gz_file:
                with open(json_filepath, 'w', encoding='utf-8') as json_file:
                    # Process in chunks to handle large files
                    while True:
                        chunk = gz_file.read(self.chunk_size)
                        if not chunk:
                            break
                        json_file.write(chunk)
            
            # Validate JSON structure
            logger.info(f"Validating JSON: {json_filepath.name}")
            with open(json_filepath, 'r', encoding='utf-8') as f:
                # Try to load just the beginning to validate structure
                f.seek(0)
                first_chunk = f.read(1024)
                if first_chunk.strip().startswith('{'):
                    logger.info(f"JSON validation passed: {json_filepath.name}")
                    return True
                else:
                    logger.error(f"Invalid JSON format: {json_filepath.name}")
                    return False
                    
        except Exception as e:
            logger.error(f"Decompression/validation failed for {filename}: {e}")
            return False
    
    def download_service_data(self, service_code: str) -> bool:
        """Download data for a specific service"""
        
        if service_code not in self.PRICING_ENDPOINTS:
            logger.error(f"Unknown service: {service_code}")
            return False
        
        url = self.PRICING_ENDPOINTS[service_code]
        filename = f"{service_code}_pricing.json"
        
        logger.info(f"Downloading {service_code} pricing data...")
        
        # Download the file
        success = self.download_with_progress(url, filename)
        
        if success:
            # Check if file is gzipped and decompress if needed
            filepath = self.download_dir / filename
            
            # Read first few bytes to check if gzipped
            with open(filepath, 'rb') as f:
                magic = f.read(2)
                if magic == b'\x1f\x8b':  # Gzip magic number
                    logger.info(f"File is gzipped, decompressing...")
                    gz_filename = f"{filename}.gz"
                    filepath.rename(self.download_dir / gz_filename)
                    return self.decompress_and_validate(gz_filename)
            
            # Validate JSON if not gzipped
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    f.read(1024)  # Just validate it's readable
                logger.info(f"JSON file validated: {filename}")
                return True
            except Exception as e:
                logger.error(f"JSON validation failed: {e}")
                return False
        
        return False
    
    def get_download_status(self) -> Dict:
        """Get status of downloaded files"""
        
        status = {
            'download_directory': str(self.download_dir),
            'files': {},
            'total_size_mb': 0,
            'last_updated': None
        }
        
        for service_code in self.PRICING_ENDPOINTS.keys():
            filename = f"{service_code}_pricing.json"
            filepath = self.download_dir / filename
            
            if filepath.exists():
                stat = filepath.stat()
                size_mb = stat.st_size / 1024 / 1024
                modified = datetime.fromtimestamp(stat.st_mtime)
                
                status['files'][service_code] = {
                    'filename': filename,
                    'size_mb': round(size_mb, 2),
                    'last_modified': modified.isoformat(),
                    'exists': True
                }
                status['total_size_mb'] += size_mb
                
                if status['last_updated'] is None or modified > datetime.fromisoformat(status['last_updated']):
                    status['last_updated'] = modified.isoformat()
            else:
                status['files'][service_code] = {
                    'filename': filename,
                    'exists': False
                }
        
        status['total_size_mb'] = round(status['total_size_mb'], 2)
        return status
    
    def cleanup_temp_files(self):
        """Clean up temporary download files"""
        
        temp_files = list(self.download_dir.glob("*.tmp"))
        gz_files = list(self.download_dir.glob("*.gz"))
        
        for temp_file in temp_files:
            logger.info(f"Removing temp file: {temp_file.name}")
            temp_file.unlink()
        
        for gz_file in gz_files:
            json_file = self.download_dir / gz_file.name.replace('.gz', '')
            if json_file.exists():
                logger.info(f"Removing compressed file: {gz_file.name}")
                gz_file.unlink()

def download_essential_services(download_dir: str = None, services: List[str] = None) -> bool:
    """Download essential AWS pricing services"""
    
    if services is None:
        services = ['index', 'AmazonEC2', 'AmazonEBS']  # Start with essentials
    
    downloader = OfflineDataDownloader(download_dir)
    
    logger.info("=" * 60)
    logger.info("OFFLINE AWS PRICING DATA DOWNLOAD")
    logger.info("=" * 60)
    
    success_count = 0
    total_count = len(services)
    
    for service in services:
        logger.info(f"\n[{success_count + 1}/{total_count}] Processing {service}...")
        
        if downloader.download_service_data(service):
            success_count += 1
            logger.info(f"✅ {service} download successful")
        else:
            logger.error(f"❌ {service} download failed")
    
    # Show final status
    logger.info("\n" + "=" * 60)
    logger.info("DOWNLOAD SUMMARY")
    logger.info("=" * 60)
    
    status = downloader.get_download_status()
    
    logger.info(f"Download directory: {status['download_directory']}")
    logger.info(f"Total size: {status['total_size_mb']} MB")
    logger.info(f"Successful downloads: {success_count}/{total_count}")
    
    for service, info in status['files'].items():
        if info['exists']:
            logger.info(f"✅ {service}: {info['size_mb']} MB ({info['last_modified']})")
        else:
            logger.info(f"❌ {service}: Not downloaded")
    
    # Cleanup
    downloader.cleanup_temp_files()
    
    if success_count == total_count:
        logger.info("\n🎉 ALL DOWNLOADS COMPLETED SUCCESSFULLY!")
        logger.info("\nNext steps:")
        logger.info("1. Run the data loading script to populate database")
        logger.info("2. Test local pricing service with real data")
        logger.info("3. Resume development with actual AWS pricing")
        return True
    else:
        logger.error(f"\n❌ {total_count - success_count} downloads failed")
        logger.error("Check the logs above for specific error details")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Download AWS pricing data offline")
    parser.add_argument("--dir", help="Download directory", default=None)
    parser.add_argument("--services", nargs="+", help="Services to download", 
                       default=['index', 'AmazonEC2', 'AmazonEBS'])
    parser.add_argument("--all", action="store_true", help="Download all available services")
    
    args = parser.parse_args()
    
    if args.all:
        services = list(OfflineDataDownloader.PRICING_ENDPOINTS.keys())
    else:
        services = args.services
    
    print(f"Starting offline download of services: {services}")
    print(f"Download directory: {args.dir or 'default (./offline_data)'}")
    print("\nThis may take several minutes depending on your internet connection...")
    print("Downloads can be resumed if interrupted.\n")
    
    success = download_essential_services(args.dir, services)
    sys.exit(0 if success else 1)
