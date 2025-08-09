# Real AWS Pricing Data - Execution Guide

**Date**: July 30, 2025  
**Purpose**: Complete Phase 1 of bulk pricing development with real AWS data  
**Estimated Time**: 4-6 hours total  

---

## 🎯 **QUICK START (3 Commands)**

```bash
# 1. Download real AWS pricing data (10-30 minutes)
cd ./enhanced-ux/backend
python3 services/bulk_pricing/offline_data_downloader.py

# 2. Load data into database (5-15 minutes)
python3 services/bulk_pricing/offline_data_loader.py --validate

# 3. Test complete setup (2-5 minutes)
python3 test_real_data_setup.py
```

**Result**: Local pricing service with real AWS data, ready for integration.

---

## 📋 **DETAILED EXECUTION STEPS**

### **Step 1: Download Real AWS Pricing Data**

```bash
cd ./enhanced-ux/backend
python3 services/bulk_pricing/offline_data_downloader.py
```

**What this does**:
- Downloads real AWS pricing files from AWS public endpoints
- Handles large files (200MB+) with resume capability
- Shows progress and download speeds
- Validates downloaded data

**Expected output**:
```
Starting download of services: ['index', 'AmazonEC2', 'AmazonEBS']
Download directory: ./services/bulk_pricing/offline_data

[1/3] Processing index...
index_pricing.json: 100.0% (1.2MB/1.2MB) - 5.23 MB/s
✅ index download successful

[2/3] Processing AmazonEC2...
AmazonEC2_pricing.json: 100.0% (198.5MB/198.5MB) - 12.45 MB/s
✅ AmazonEC2 download successful

[3/3] Processing AmazonEBS...
AmazonEBS_pricing.json: 100.0% (52.3MB/52.3MB) - 8.91 MB/s
✅ AmazonEBS download successful

🎉 ALL DOWNLOADS COMPLETED SUCCESSFULLY!
```

**If download fails**:
- Downloads are resumable - just run the command again
- For slower connections, use: `--services AmazonEC2` (essential only)
- Check internet connection and disk space

### **Step 2: Load Data into Database**

```bash
python3 services/bulk_pricing/offline_data_loader.py --validate
```

**What this does**:
- Processes downloaded JSON files in memory-efficient batches
- Loads pricing data into SQLite database
- Validates data integrity and completeness
- Shows loading progress and statistics

**Expected output**:
```
LOADING REAL AWS PRICING DATA
============================================================

Found 3 data files:
  AmazonEC2_pricing.json: 198.5MB
  AmazonEBS_pricing.json: 52.3MB
  index_pricing.json: 1.2MB

[Loading] AmazonEC2...
Processing EC2 pricing data...
Processed batch: 1000 records (total: 1000)
Processed batch: 1000 records (total: 2000)
...
EC2 processing complete: 45,234 total records
✅ AmazonEC2 loaded successfully

[Loading] AmazonEBS...
Processing EBS pricing data...
EBS processing complete: 8,456 total records
✅ AmazonEBS loaded successfully

LOADING SUMMARY
============================================================
Successful loads: 3/3
Records added: 53,690
Total database records: 53,690

🎉 ALL DATA LOADED SUCCESSFULLY!
```

### **Step 3: Test Complete Setup**

```bash
python3 test_real_data_setup.py
```

**What this does**:
- Validates all components are working
- Tests pricing lookups with real data
- Benchmarks performance
- Confirms integration readiness

**Expected output**:
```
🧪 TESTING BULK PRICING WITH REAL AWS DATA
============================================================

📥 Test 1: Check Downloaded Data
✅ Found downloaded data for 3 services
✅ Total data size: 251.8 MB

📊 Test 2: Database Status
✅ Database path: ./services/pricing_database.db
✅ Total records: 53,690

🏪 Test 4: Local Pricing Service
✅ Health status: healthy
✅ Response time: 2ms
✅ Database records: 53,690

💰 Test 5: Real Pricing Lookups
✅ m5.large in us-east-1: $0.0960/hour
   Reserved 1yr: $0.0672/hour (30.0% savings)
✅ c5.xlarge in us-west-2: $0.1785/hour
✅ r5.2xlarge in eu-west-1: $0.5712/hour

⚡ Test 6: Performance Benchmarks
✅ 100 pricing lookups in 0.045s
✅ Average lookup time: 0.45ms
✅ Throughput: 2,222 lookups/sec

🎉 ALL REAL DATA TESTS PASSED!
```

---

## 🔗 **INTEGRATION WITH EXISTING SERVICES**

After successful setup, integrate with your existing cost calculation services:

### **Update cost_estimates_service.py**

```python
# Replace AWS API calls with local pricing
from services.bulk_pricing.local_pricing_service import LocalPricingService

class CostEstimatesService:
    def __init__(self):
        # Use local pricing instead of AWS API
        self.pricing_service = LocalPricingService()
    
    async def get_instance_cost(self, instance_type: str, region: str) -> float:
        """Get instance cost using local pricing data"""
        try:
            pricing = await self.pricing_service.get_instance_pricing(instance_type, region)
            return pricing.on_demand_price_per_hour if pricing else 0.0
        except Exception as e:
            logger.error(f"Failed to get pricing for {instance_type} in {region}: {e}")
            return 0.0
```

### **Test Integration**

```python
# Test the integration
cost_service = CostEstimatesService()
monthly_cost = await cost_service.calculate_monthly_cost('m5.large', 'us-east-1')
print(f"Monthly cost: ${monthly_cost:.2f}")
```

---

## 🔧 **TROUBLESHOOTING**

### **Download Issues**

**Problem**: Download fails or is very slow
```bash
# Solution 1: Resume interrupted download
python3 services/bulk_pricing/offline_data_downloader.py

# Solution 2: Download essential services only
python3 services/bulk_pricing/offline_data_downloader.py --services AmazonEC2

# Solution 3: Check available disk space
df -h .
```

### **Loading Issues**

**Problem**: Database loading fails
```bash
# Solution 1: Check database permissions
ls -la services/pricing_database.db

# Solution 2: Use smaller batch size
python3 services/bulk_pricing/offline_data_loader.py --batch-size 500

# Solution 3: Check available memory
free -h
```

### **Performance Issues**

**Problem**: Slow pricing lookups
```bash
# Solution 1: Rebuild database indexes
python3 -c "from services.bulk_pricing.database import PricingDatabase; db = PricingDatabase(); db._create_indexes()"

# Solution 2: Check database size and location
ls -lh services/pricing_database.db
```

---

## 📊 **SUCCESS CRITERIA**

✅ **Downloads Complete**: All pricing files downloaded successfully  
✅ **Database Loaded**: 50,000+ pricing records in SQLite database  
✅ **Performance**: Sub-millisecond pricing lookups  
✅ **Accuracy**: Real AWS pricing data, not estimates  
✅ **Integration Ready**: Compatible with existing cost calculation services  

---

## 🚀 **NEXT STEPS AFTER COMPLETION**

1. **Integrate with existing services** (2-3 hours)
2. **Test end-to-end cost calculations** with real RVTools data
3. **Set up automated data refresh** (weekly/monthly)
4. **Move to Phase 2 enhancements** (advanced indexing, monitoring)

---

**Status**: ✅ **READY FOR EXECUTION**  
**Estimated Time**: 4-6 hours for complete setup  
**Result**: Production-ready local pricing service with real AWS data
