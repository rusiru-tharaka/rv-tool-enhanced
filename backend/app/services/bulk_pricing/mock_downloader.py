"""
Mock Bulk Price Downloader
Replaces the problematic real downloader with instant sample data
Allows development to proceed without network dependencies
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

from .sample_data_generator import SampleDataGenerator

logger = logging.getLogger(__name__)

class MockBulkPriceDownloader:
    """Mock downloader that returns sample data instantly"""
    
    def __init__(self, cache_dir: str = None):
        """Initialize mock downloader"""
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / "pricing_cache"
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.generator = SampleDataGenerator()
        self._sample_data_cache = {}
        
        logger.info(f"Mock bulk price downloader initialized with cache: {self.cache_dir}")
    
    def download_service_pricing(self, service_code: str, force_refresh: bool = False) -> Optional[Dict]:
        """Return mock pricing data instantly"""
        
        logger.info(f"Mock download for service: {service_code}")
        
        if service_code == 'index':
            return self._get_mock_index_data()
        elif service_code == 'AmazonEC2':
            return self._get_mock_ec2_data()
        elif service_code == 'AmazonEBS':
            return self._get_mock_ebs_data()
        else:
            logger.warning(f"Mock data not available for service: {service_code}")
            return None
    
    def _get_mock_index_data(self) -> Dict:
        """Return mock AWS pricing index"""
        return {
            "formatVersion": "v1.0",
            "disclaimer": "Mock data for development - not real AWS pricing",
            "offerCode": "AWSPricing",
            "version": "20250730000000",
            "publicationDate": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "offers": {
                "AmazonEC2": {
                    "offerCode": "AmazonEC2",
                    "versionIndexUrl": "/offers/v1.0/aws/AmazonEC2/index.json",
                    "currentVersionUrl": "/offers/v1.0/aws/AmazonEC2/current/index.json"
                },
                "AmazonEBS": {
                    "offerCode": "AmazonEBS", 
                    "versionIndexUrl": "/offers/v1.0/aws/AmazonEBS/index.json",
                    "currentVersionUrl": "/offers/v1.0/aws/AmazonEBS/current/index.json"
                }
            }
        }
    
    def _get_mock_ec2_data(self) -> Dict:
        """Return mock EC2 pricing data in AWS format"""
        
        if 'ec2' in self._sample_data_cache:
            return self._sample_data_cache['ec2']
        
        logger.info("Generating mock EC2 pricing data...")
        
        # Generate sample data
        sample_data = self.generator.generate_complete_sample_dataset()
        ec2_records = sample_data['ec2_pricing']
        
        # Convert to AWS pricing format
        products = {}
        terms = {"OnDemand": {}, "Reserved": {}}
        
        for i, record in enumerate(ec2_records):
            product_id = f"MOCK{i:06d}"
            
            # Product definition
            products[product_id] = {
                "sku": product_id,
                "productFamily": "Compute Instance",
                "attributes": {
                    "servicecode": "AmazonEC2",
                    "servicename": "Amazon Elastic Compute Cloud",
                    "instanceType": record['instance_type'],
                    "location": record['location'],
                    "locationType": "AWS Region",
                    "operatingSystem": record['operating_system'],
                    "tenancy": record['tenancy'],
                    "preInstalledSw": "NA",
                    "capacitystatus": "Used",
                    "usagetype": f"{record['region'].replace('-', '').upper()}:BoxUsage:{record['instance_type']}"
                }
            }
            
            # Pricing terms
            term_id = f"TERM{i:06d}"
            dimension_id = f"DIM{i:06d}"
            
            if record['pricing_model'] == 'OnDemand':
                terms["OnDemand"][product_id] = {
                    term_id: {
                        "offerTermCode": "JRTCKXETXF",
                        "sku": product_id,
                        "effectiveDate": record['effective_date'],
                        "priceDimensions": {
                            dimension_id: {
                                "rateCode": f"{product_id}.{term_id}.{dimension_id}",
                                "description": f"${record['price_per_hour']} per On Demand {record['operating_system']} {record['instance_type']} Instance Hour",
                                "beginRange": "0",
                                "endRange": "Inf",
                                "unit": "Hrs",
                                "pricePerUnit": {
                                    "USD": str(record['price_per_hour'])
                                }
                            }
                        },
                        "termAttributes": {}
                    }
                }
            elif record['pricing_model'] == 'Reserved':
                if "Reserved" not in terms:
                    terms["Reserved"] = {}
                
                terms["Reserved"][product_id] = {
                    term_id: {
                        "offerTermCode": "38NPMPTW36",
                        "sku": product_id,
                        "effectiveDate": record['effective_date'],
                        "priceDimensions": {
                            dimension_id: {
                                "rateCode": f"{product_id}.{term_id}.{dimension_id}",
                                "description": f"${record['price_per_hour']} per Reserved {record['operating_system']} {record['instance_type']} Instance Hour",
                                "beginRange": "0",
                                "endRange": "Inf",
                                "unit": "Hrs",
                                "pricePerUnit": {
                                    "USD": str(record['price_per_hour'])
                                }
                            }
                        },
                        "termAttributes": {
                            "LeaseContractLength": record['term_length'],
                            "OfferingClass": "standard",
                            "PurchaseOption": record['payment_option']
                        }
                    }
                }
        
        mock_data = {
            "formatVersion": "v1.0",
            "disclaimer": "Mock EC2 pricing data for development",
            "offerCode": "AmazonEC2",
            "version": "20250730000000",
            "publicationDate": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "products": products,
            "terms": terms
        }
        
        # Cache the result
        self._sample_data_cache['ec2'] = mock_data
        
        logger.info(f"Generated mock EC2 data: {len(products)} products, {len(terms['OnDemand'])} on-demand terms")
        return mock_data
    
    def _get_mock_ebs_data(self) -> Dict:
        """Return mock EBS pricing data in AWS format"""
        
        if 'ebs' in self._sample_data_cache:
            return self._sample_data_cache['ebs']
        
        logger.info("Generating mock EBS pricing data...")
        
        # Generate sample EBS data
        sample_data = self.generator.generate_complete_sample_dataset()
        ebs_records = sample_data['ebs_pricing']
        
        # Convert to AWS pricing format
        products = {}
        terms = {"OnDemand": {}}
        
        for i, record in enumerate(ebs_records):
            product_id = f"EBSMOCK{i:06d}"
            
            # Product definition
            products[product_id] = {
                "sku": product_id,
                "productFamily": "Storage",
                "attributes": {
                    "servicecode": "AmazonEBS",
                    "servicename": "Amazon Elastic Block Store",
                    "volumeType": record['volume_type'].upper(),
                    "location": record['location'],
                    "locationType": "AWS Region",
                    "storageMedia": "SSD" if record['volume_type'] in ['gp2', 'gp3', 'io1', 'io2'] else "HDD",
                    "usagetype": f"{record['region'].replace('-', '').upper()}:VolumeUsage.{record['volume_type']}"
                }
            }
            
            # Pricing terms
            term_id = f"EBSTERM{i:06d}"
            dimension_id = f"EBSDIM{i:06d}"
            
            terms["OnDemand"][product_id] = {
                term_id: {
                    "offerTermCode": "JRTCKXETXF",
                    "sku": product_id,
                    "effectiveDate": record['effective_date'],
                    "priceDimensions": {
                        dimension_id: {
                            "rateCode": f"{product_id}.{term_id}.{dimension_id}",
                            "description": f"${record['price_per_gb_month']} per GB-month of {record['volume_type']} storage",
                            "beginRange": "0",
                            "endRange": "Inf",
                            "unit": "GB-Mo",
                            "pricePerUnit": {
                                "USD": str(record['price_per_gb_month'])
                            }
                        }
                    },
                    "termAttributes": {}
                }
            }
        
        mock_data = {
            "formatVersion": "v1.0",
            "disclaimer": "Mock EBS pricing data for development",
            "offerCode": "AmazonEBS",
            "version": "20250730000000",
            "publicationDate": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "products": products,
            "terms": terms
        }
        
        # Cache the result
        self._sample_data_cache['ebs'] = mock_data
        
        logger.info(f"Generated mock EBS data: {len(products)} products")
        return mock_data
    
    def download_all_services(self, services: List[str] = None, force_refresh: bool = False) -> Dict[str, Dict]:
        """Download multiple services (mock)"""
        
        if services is None:
            services = ['AmazonEC2', 'AmazonEBS']
        
        results = {}
        for service_code in services:
            logger.info(f"Mock downloading {service_code}...")
            data = self.download_service_pricing(service_code, force_refresh)
            if data:
                results[service_code] = data
        
        return results
    
    def get_available_services(self) -> List[str]:
        """Get list of available services (mock)"""
        return ['AmazonEC2', 'AmazonEBS']
    
    def get_cache_info(self) -> Dict:
        """Get cache information"""
        return {
            'cache_directory': str(self.cache_dir),
            'cached_services': list(self._sample_data_cache.keys()),
            'cache_type': 'mock_in_memory',
            'last_updated': datetime.now().isoformat()
        }
    
    def clear_cache(self):
        """Clear the mock cache"""
        self._sample_data_cache.clear()
        logger.info("Mock cache cleared")

# Convenience function to replace real downloader
def create_mock_downloader(cache_dir: str = None) -> MockBulkPriceDownloader:
    """Create a mock downloader instance"""
    return MockBulkPriceDownloader(cache_dir)
