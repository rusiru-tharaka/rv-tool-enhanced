"""
AWS Bulk Price List Downloader
Downloads pricing data from AWS bulk pricing endpoints
"""

import requests
import json
import logging
import gzip
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class BulkPriceDownloader:
    """Downloads AWS bulk pricing data"""
    
    # AWS Bulk Pricing Endpoints
    PRICING_ENDPOINTS = {
        'index': 'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/index.json',
        'AmazonEC2': 'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/index.json',
        'AmazonEBS': 'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEBS/current/index.json',
        'AmazonRDS': 'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/index.json',
        'AmazonS3': 'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/index.json'
    }
    
    # All AWS Regions
    AWS_REGIONS = [
        'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
        'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-central-1', 'eu-north-1', 'eu-south-1',
        'ap-southeast-1', 'ap-southeast-2', 'ap-southeast-3', 'ap-northeast-1', 'ap-northeast-2', 'ap-northeast-3', 'ap-south-1', 'ap-east-1',
        'ca-central-1', 'sa-east-1', 'af-south-1', 'me-south-1', 'me-central-1',
        'us-gov-east-1', 'us-gov-west-1'
    ]
    
    def __init__(self, cache_dir: str = None):
        """Initialize downloader with cache directory"""
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / "pricing_cache"
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Request session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RVTool-Pricing-Service/1.0',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate'
        })
        
        logger.info(f"Bulk price downloader initialized with cache: {self.cache_dir}")
    
    def download_service_pricing(self, service_code: str, force_refresh: bool = False) -> Optional[Dict]:
        """Download pricing data for a specific AWS service"""
        
        if service_code not in self.PRICING_ENDPOINTS:
            logger.error(f"Unknown service code: {service_code}")
            return None
        
        url = self.PRICING_ENDPOINTS[service_code]
        cache_file = self.cache_dir / f"{service_code}_pricing.json"
        
        # Check if cached file exists and is recent (unless force refresh)
        if not force_refresh and cache_file.exists():
            file_age_hours = (datetime.now().timestamp() - cache_file.stat().st_mtime) / 3600
            if file_age_hours < 24:  # Use cache if less than 24 hours old
                logger.info(f"Using cached pricing data for {service_code} (age: {file_age_hours:.1f} hours)")
                try:
                    with open(cache_file, 'r') as f:
                        return json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load cached data for {service_code}: {e}")
        
        # Download fresh data
        logger.info(f"Downloading pricing data for {service_code} from {url}")
        start_time = time.time()
        
        try:
            response = self.session.get(url, timeout=300)  # 5 minute timeout
            response.raise_for_status()
            
            # Handle gzipped content
            if response.headers.get('content-encoding') == 'gzip':
                content = gzip.decompress(response.content).decode('utf-8')
                pricing_data = json.loads(content)
            else:
                pricing_data = response.json()
            
            download_time = time.time() - start_time
            file_size_mb = len(response.content) / (1024 * 1024)
            
            logger.info(f"Downloaded {service_code} pricing data: {file_size_mb:.1f}MB in {download_time:.1f}s")
            
            # Cache the data
            try:
                with open(cache_file, 'w') as f:
                    json.dump(pricing_data, f, separators=(',', ':'))  # Compact JSON
                logger.info(f"Cached pricing data to {cache_file}")
            except Exception as e:
                logger.warning(f"Failed to cache pricing data: {e}")
            
            return pricing_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download pricing data for {service_code}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON for {service_code}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading {service_code}: {e}")
            return None
    
    def download_all_services(self, services: List[str] = None, force_refresh: bool = False) -> Dict[str, Dict]:
        """Download pricing data for multiple services"""
        
        if services is None:
            services = ['AmazonEC2', 'AmazonEBS']  # Default to core services
        
        results = {}
        total_start_time = time.time()
        
        logger.info(f"Starting bulk download for {len(services)} services")
        
        for service_code in services:
            service_start_time = time.time()
            
            try:
                pricing_data = self.download_service_pricing(service_code, force_refresh)
                if pricing_data:
                    results[service_code] = pricing_data
                    service_time = time.time() - service_start_time
                    logger.info(f"✅ {service_code}: Downloaded in {service_time:.1f}s")
                else:
                    logger.error(f"❌ {service_code}: Download failed")
                    
            except Exception as e:
                logger.error(f"❌ {service_code}: Unexpected error - {e}")
        
        total_time = time.time() - total_start_time
        success_count = len(results)
        
        logger.info(f"Bulk download completed: {success_count}/{len(services)} services in {total_time:.1f}s")
        
        return results
    
    def get_available_services(self) -> List[str]:
        """Get list of available AWS services from index"""
        
        try:
            index_data = self.download_service_pricing('index')
            if index_data and 'offers' in index_data:
                services = list(index_data['offers'].keys())
                logger.info(f"Found {len(services)} available AWS services")
                return services
            else:
                logger.warning("No services found in index data")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get available services: {e}")
            return []
    
    def validate_download(self, service_code: str, pricing_data: Dict) -> bool:
        """Validate downloaded pricing data structure"""
        
        if not pricing_data:
            return False
        
        # Basic structure validation
        required_keys = ['formatVersion', 'disclaimer', 'offerCode', 'version']
        if not all(key in pricing_data for key in required_keys):
            logger.error(f"Missing required keys in {service_code} pricing data")
            return False
        
        # Service-specific validation
        if service_code == 'AmazonEC2':
            if 'products' not in pricing_data or 'terms' not in pricing_data:
                logger.error(f"Missing products or terms in {service_code} data")
                return False
            
            products_count = len(pricing_data.get('products', {}))
            terms_count = len(pricing_data.get('terms', {}))
            
            if products_count < 1000:  # EC2 should have thousands of products
                logger.warning(f"Suspiciously low product count for {service_code}: {products_count}")
                return False
            
            logger.info(f"Validation passed for {service_code}: {products_count} products, {terms_count} term types")
        
        return True
    
    def get_cache_info(self) -> Dict:
        """Get information about cached pricing files"""
        
        cache_info = {}
        
        for service_code in self.PRICING_ENDPOINTS.keys():
            cache_file = self.cache_dir / f"{service_code}_pricing.json"
            
            if cache_file.exists():
                stat = cache_file.stat()
                age_hours = (datetime.now().timestamp() - stat.st_mtime) / 3600
                size_mb = stat.st_size / (1024 * 1024)
                
                cache_info[service_code] = {
                    'exists': True,
                    'age_hours': age_hours,
                    'size_mb': size_mb,
                    'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
            else:
                cache_info[service_code] = {'exists': False}
        
        return cache_info
    
    def clear_cache(self, service_code: str = None):
        """Clear cached pricing data"""
        
        if service_code:
            cache_file = self.cache_dir / f"{service_code}_pricing.json"
            if cache_file.exists():
                cache_file.unlink()
                logger.info(f"Cleared cache for {service_code}")
        else:
            # Clear all cache files
            for cache_file in self.cache_dir.glob("*_pricing.json"):
                cache_file.unlink()
            logger.info("Cleared all pricing cache files")
    
    def close(self):
        """Close the requests session"""
        self.session.close()
