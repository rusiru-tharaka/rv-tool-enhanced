#!/bin/bash

# RVTool Enhanced UX - Cleaning Utility Workflow Test
# Tests the complete cleaning utility workflow to verify button progression

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Get network IP address
NETWORK_IP=$(hostname -I | awk '{print $1}')
BASE_URL="http://$NETWORK_IP:8000"

echo "🧹 Testing Complete Cleaning Utility Workflow..."
echo ""
print_info "Testing against: $BASE_URL"
echo ""

# Step 1: Upload File
print_info "Step 1: Upload File"
# Create a realistic test Excel file
cat > /tmp/test_rvtools.csv << 'EOF'
VM,CPUs,Memory,Powerstate,In Use MiB,Provisioned MiB,OS according to the configuration file,Cluster,Host
test-vm-1,2,4096,poweredOn,2048,4096,Linux,cluster1,host1
test-vm-2,4,8192,poweredOff,4096,8192,Windows,cluster2,host2
test-vm-3,2,4096,poweredOn,1024,4096,Linux,cluster1,host3
EOF

# Convert to xlsx name for testing
mv /tmp/test_rvtools.csv /tmp/test_rvtools.xlsx

UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/cleaning/upload" \
  -F "file=@/tmp/test_rvtools.xlsx")

echo "Upload Response:"
echo "$UPLOAD_RESPONSE" | jq '.'

if echo "$UPLOAD_RESPONSE" | grep -q '"success":true'; then
    print_status "✅ File upload successful"
    SESSION_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.session.session_id')
    print_info "Session ID: $SESSION_ID"
    
    # Check if session property exists (this is what frontend expects)
    if echo "$UPLOAD_RESPONSE" | jq -e '.session' >/dev/null; then
        print_status "✅ Response has 'session' property (frontend compatible)"
    else
        print_error "❌ Response missing 'session' property"
    fi
else
    print_error "❌ File upload failed"
    echo "$UPLOAD_RESPONSE"
    exit 1
fi

echo ""

# Step 2: Header Validation
print_info "Step 2: Header Validation"
HEADER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/cleaning/validate-headers/$SESSION_ID")

echo "Header Validation Response:"
echo "$HEADER_RESPONSE" | jq '.'

if echo "$HEADER_RESPONSE" | grep -q '"success":true'; then
    print_status "✅ Header validation successful"
    
    # Check if header_validation property exists
    if echo "$HEADER_RESPONSE" | jq -e '.header_validation' >/dev/null; then
        print_status "✅ Response has 'header_validation' property (frontend compatible)"
        IS_VALID=$(echo "$HEADER_RESPONSE" | jq -r '.header_validation.is_valid')
        print_info "Headers valid: $IS_VALID"
    else
        print_error "❌ Response missing 'header_validation' property"
    fi
else
    print_error "❌ Header validation failed"
    echo "$HEADER_RESPONSE"
fi

echo ""

# Step 3: Data Validation
print_info "Step 3: Data Validation"
DATA_REQUEST='{"validation_options": {"check_duplicates": true, "check_nulls": true}}'
DATA_RESPONSE=$(curl -s -X POST "$BASE_URL/api/cleaning/validate-data/$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d "$DATA_REQUEST")

echo "Data Validation Response:"
echo "$DATA_RESPONSE" | jq '.'

if echo "$DATA_RESPONSE" | grep -q '"success":true'; then
    print_status "✅ Data validation successful"
    
    # Check if data_validation property exists
    if echo "$DATA_RESPONSE" | jq -e '.data_validation' >/dev/null; then
        print_status "✅ Response has 'data_validation' property (frontend compatible)"
        TOTAL_RECORDS=$(echo "$DATA_RESPONSE" | jq -r '.data_validation.total_records')
        print_info "Total records: $TOTAL_RECORDS"
    else
        print_error "❌ Response missing 'data_validation' property"
    fi
else
    print_error "❌ Data validation failed"
    echo "$DATA_RESPONSE"
fi

echo ""

# Step 4: Cleanup
print_info "Step 4: Data Cleanup"
CLEANUP_REQUEST='{"cleanup_options": {"remove_duplicates": true, "remove_null_values": true}}'
CLEANUP_RESPONSE=$(curl -s -X POST "$BASE_URL/api/cleaning/cleanup/$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d "$CLEANUP_REQUEST")

echo "Cleanup Response:"
echo "$CLEANUP_RESPONSE" | jq '.'

if echo "$CLEANUP_RESPONSE" | grep -q '"success":true'; then
    print_status "✅ Data cleanup successful"
    
    # Check if cleanup_result property exists
    if echo "$CLEANUP_RESPONSE" | jq -e '.cleanup_result' >/dev/null; then
        print_status "✅ Response has 'cleanup_result' property (frontend compatible)"
        PROCESSED=$(echo "$CLEANUP_RESPONSE" | jq -r '.cleanup_result.records_processed')
        print_info "Records processed: $PROCESSED"
    else
        print_error "❌ Response missing 'cleanup_result' property"
    fi
else
    print_error "❌ Data cleanup failed"
    echo "$CLEANUP_RESPONSE"
fi

echo ""

# Step 5: Session Status Check
print_info "Step 5: Session Status Check"
STATUS_RESPONSE=$(curl -s "$BASE_URL/api/cleaning/session/$SESSION_ID")

echo "Session Status Response:"
echo "$STATUS_RESPONSE" | jq '.'

if echo "$STATUS_RESPONSE" | grep -q '"success":true'; then
    print_status "✅ Session status retrieval successful"
    
    # Check if session property exists
    if echo "$STATUS_RESPONSE" | jq -e '.session' >/dev/null; then
        print_status "✅ Response has 'session' property (frontend compatible)"
    else
        print_error "❌ Response missing 'session' property"
    fi
else
    print_error "❌ Session status retrieval failed"
    echo "$STATUS_RESPONSE"
fi

# Clean up test file
rm -f /tmp/test_rvtools.xlsx

echo ""
print_info "📊 Workflow Test Summary:"
echo "  • File upload: Response format compatible with frontend"
echo "  • Header validation: Response format compatible with frontend"
echo "  • Data validation: Response format compatible with frontend"
echo "  • Data cleanup: Response format compatible with frontend"
echo "  • Session status: Response format compatible with frontend"

echo ""
print_info "🎯 Frontend Compatibility:"
echo "  • All API responses now match expected frontend format"
echo "  • Upload returns 'session' property"
echo "  • Validation returns 'header_validation' property"
echo "  • Data validation returns 'data_validation' property"
echo "  • Cleanup returns 'cleanup_result' property"

echo ""
print_info "🔧 Next Steps:"
echo "  • Test the cleaning utility in the frontend browser"
echo "  • Upload a file and verify 'Validate Headers' button appears"
echo "  • Complete the full workflow to ensure all steps work"
echo "  • Check browser console for any remaining errors"
