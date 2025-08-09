# Cost Discrepancy Investigation Plan

**Date**: July 30, 2025  
**Issue**: Cost discrepancies in Instance Cost, Storage Cost, and Total Cost  
**Data Source**: RVTools_Sample_4  
**Export File**: vm-cost-estimates-65f48983-58c1-43a3-9dc9-050d7b10ee50  
**Region**: Singapore (ap-southeast-1)  
**TCO Parameters**:
- Production Workloads: Reserved Instance, 3-year term, No Upfront
- Non-Production: On-Demand, 50% utilization

---

## 🎯 **INVESTIGATION OBJECTIVES**

1. **Identify Root Causes** of cost calculation discrepancies
2. **Validate Pricing Data** for Singapore region
3. **Verify Calculation Logic** for Reserved Instance and On-Demand pricing
4. **Assess Data Flow** from RVTools input to CSV export
5. **Develop Fix Strategy** with comprehensive testing

---

## 📋 **PHASE 1: DATA ANALYSIS & VALIDATION**

### **Step 1.1: Examine Source Data**
- [ ] Analyze RVTools_Sample_4 file structure and VM specifications
- [ ] Validate VM categorization (Production vs Non-Production)
- [ ] Check CPU, Memory, and Storage specifications
- [ ] Identify any data quality issues

### **Step 1.2: Analyze Exported CSV**
- [ ] Review vm-cost-estimates CSV for calculation patterns
- [ ] Identify specific VMs with discrepancies
- [ ] Compare Instance Cost vs expected calculations
- [ ] Analyze Storage Cost calculations
- [ ] Validate Total Cost summations

### **Step 1.3: Cross-Reference with Expected Values**
- [ ] Manual calculation verification for sample VMs
- [ ] Compare with AWS Pricing Calculator results
- [ ] Validate Singapore region pricing accuracy

---

## 🔍 **PHASE 2: TECHNICAL INVESTIGATION**

### **Step 2.1: Backend Service Analysis**
- [ ] Examine cost_estimates_service.py calculation logic
- [ ] Validate Reserved Instance pricing calculations
- [ ] Check On-Demand pricing with utilization factors
- [ ] Review Singapore region pricing data

### **Step 2.2: Pricing Service Validation**
- [ ] Test aws_pricing_service.py for Singapore region
- [ ] Validate local pricing cache accuracy
- [ ] Check API fallback mechanisms
- [ ] Verify Reserved Instance pricing formulas

### **Step 2.3: Instance Recommendation Analysis**
- [ ] Review VM-to-EC2 instance type mapping
- [ ] Validate instance sizing recommendations
- [ ] Check regional instance availability
- [ ] Analyze storage type recommendations

---

## 🧪 **PHASE 3: SYSTEMATIC TESTING**

### **Step 3.1: Unit Testing**
- [ ] Test individual cost calculation functions
- [ ] Validate pricing lookup mechanisms
- [ ] Test utilization factor applications
- [ ] Verify currency and regional adjustments

### **Step 3.2: Integration Testing**
- [ ] End-to-end testing with RVTools_Sample_4
- [ ] Validate complete workflow from upload to export
- [ ] Test different TCO parameter combinations
- [ ] Verify CSV export accuracy

### **Step 3.3: Regression Testing**
- [ ] Compare with previous working calculations
- [ ] Test with other sample data sets
- [ ] Validate against known good results

---

## 🔧 **PHASE 4: FIX STRATEGY DEVELOPMENT**

### **Step 4.1: Root Cause Classification**
- [ ] Pricing data issues (incorrect rates)
- [ ] Calculation logic errors (formula problems)
- [ ] Data transformation issues (unit conversions)
- [ ] Regional configuration problems

### **Step 4.2: Fix Implementation Priority**
1. **Critical**: Incorrect pricing data or major calculation errors
2. **High**: Formula logic issues affecting accuracy
3. **Medium**: Data transformation or formatting issues
4. **Low**: Minor display or rounding discrepancies

### **Step 4.3: Validation Framework**
- [ ] Create test cases for each identified issue
- [ ] Implement automated validation checks
- [ ] Establish baseline accuracy metrics
- [ ] Create regression test suite

---

## 📊 **INVESTIGATION TOOLS & METHODS**

### **Data Analysis Tools**
- Python scripts for CSV analysis
- Excel/spreadsheet validation
- AWS Pricing Calculator cross-reference
- Database query validation

### **Testing Approaches**
- Unit tests for individual functions
- Integration tests for complete workflows
- Manual calculation verification
- Automated regression testing

### **Monitoring & Validation**
- Cost calculation accuracy metrics
- Regional pricing validation
- Performance impact assessment
- User acceptance testing

---

## 🎯 **SUCCESS CRITERIA**

### **Accuracy Targets**
- [ ] Instance Cost calculations within 1% of expected values
- [ ] Storage Cost calculations accurate to actual AWS pricing
- [ ] Total Cost summations mathematically correct
- [ ] Regional pricing reflects current Singapore rates

### **Quality Assurance**
- [ ] All test cases pass validation
- [ ] No regression in other regions or scenarios
- [ ] Performance maintained or improved
- [ ] Documentation updated with fixes

---

## 📅 **EXECUTION TIMELINE**

### **Phase 1: Data Analysis** (Day 1-2)
- Complete data examination and initial analysis
- Identify specific discrepancy patterns
- Document findings and scope

### **Phase 2: Technical Investigation** (Day 2-3)
- Deep dive into backend services
- Validate pricing and calculation logic
- Identify root causes

### **Phase 3: Testing & Validation** (Day 3-4)
- Systematic testing of identified issues
- Develop comprehensive test cases
- Validate fix approaches

### **Phase 4: Implementation & Deployment** (Day 4-5)
- Implement fixes with proper testing
- Deploy and validate in production
- Monitor for any regressions

---

## 🚨 **RISK MITIGATION**

### **Backup Strategy**
- [ ] Create backup of current working system
- [ ] Implement feature flags for new calculations
- [ ] Maintain rollback capability

### **Testing Safety**
- [ ] Test in isolated environment first
- [ ] Validate with multiple data sets
- [ ] Gradual rollout with monitoring

### **Communication Plan**
- [ ] Document all changes and rationale
- [ ] Provide clear before/after comparisons
- [ ] Update user documentation as needed

---

**Next Action**: Begin Phase 1 data analysis with RVTools_Sample_4 and exported CSV examination.
