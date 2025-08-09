# Singapore TCO Test - Quick Reference Guide

**Document Type**: 📋 **LIVE DOCUMENT** - Quick Reference  
**Last Updated**: July 31, 2025  
**Version**: 1.0.0  

---

## 🚀 **QUICK ACCESS**

### **URLs**:
- **Page**: `/singapore-tco-test/{sessionId}`
- **API**: `POST /api/singapore-tco-test/{sessionId}`
- **Documentation**: `./SINGAPORE_TCO_COMPREHENSIVE_DOCUMENTATION.md`

### **Key Files**:
```
Frontend:
├── src/pages/SingaporeTCOTest.tsx          # Main page component
├── src/components/TCOParametersForm.tsx    # Access button
├── src/App.tsx                             # Routing
└── src/services/api.ts                     # API integration

Backend:
├── routers/singapore_tco_test.py           # Main router & logic
├── services/session_manager.py             # Session management
└── services/instance_recommendation_service.py  # Instance recommendations
```

---

## ⚡ **QUICK TROUBLESHOOTING**

### **Common Issues & Solutions**:

| Issue | Quick Fix |
|-------|-----------|
| "Session not found" | Upload RVTools file first, get new session ID |
| "No VM data" | Verify RVTools file uploaded successfully |
| Page won't load | Check backend running on port 8000 |
| Wrong costs | Update Singapore pricing data in router |
| CSV export fails | Check browser download permissions |

### **Debug Commands**:
```bash
# Check backend status
curl http://localhost:8000/health

# Test Singapore TCO API
curl -X POST http://localhost:8000/api/singapore-tco-test/{session_id} \
  -H "Content-Type: application/json" \
  -d '{"target_region": "ap-southeast-1"}'

# Check frontend build
cd frontend && npm run build
```

---

## 🔧 **HARDCODED PARAMETERS**

### **Production VMs**:
- **Pricing**: 3-Year Reserved Instance (No Upfront)
- **Utilization**: 100%
- **Classification**: Contains 'prod', 'dr', 'backup', 'archive' OR large VMs (4+ CPU, 16+ GB)

### **Non-Production VMs**:
- **Pricing**: On-Demand
- **Utilization**: 50%
- **Classification**: Contains 'dev', 'test', 'uat', 'demo', 'staging' OR small VMs

### **Sample Pricing** (Singapore):
```
t3.xlarge:  On-Demand $0.2048/hr, 3yr RI $0.1232/hr
m5.xlarge:  On-Demand $0.232/hr,  3yr RI $0.140/hr
Storage:    GP3 $0.092/GB/month
```

---

## 📊 **CALCULATION FORMULA**

```
Monthly Cost = (Hourly_Rate × 730.56 × Utilization) + (Storage_GB × $0.092)

Production:     (RI_Rate × 730.56 × 1.0) + Storage_Cost
Non-Production: (OnDemand_Rate × 730.56 × 0.5) + Storage_Cost
```

---

## 🔄 **UPDATE CHECKLIST**

When making changes:
- [ ] Update version number in documentation
- [ ] Update "Last Updated" date
- [ ] Test all functionality
- [ ] Update pricing data if needed
- [ ] Commit changes with descriptive message
- [ ] Update this quick reference if needed

---

## 📞 **EMERGENCY CONTACTS**

- **Backend Issues**: Check backend logs, restart service
- **Frontend Issues**: Clear browser cache, check console errors
- **Pricing Issues**: Update SINGAPORE_PRICING in router
- **Documentation**: Update comprehensive documentation file

---

**For complete details, see**: `SINGAPORE_TCO_COMPREHENSIVE_DOCUMENTATION.md`
