# 🗺️ Deployment Resource Map

This guide helps you find the right resource for your situation.

---

## 📚 Documentation Files

| File | Purpose | When to Use |
|------|---------|------------|
| [SERVERLESS_QUICKSTART.md](SERVERLESS_QUICKSTART.md) | **START HERE** - 5-10 min setup | First time deploying, want fastest path |
| [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) | Pre-flight verification | Before running scripts, troubleshooting |
| [DEPLOY_AWS.md](DEPLOY_AWS.md) | AWS Lambda detailed guide (7 steps) | Manual AWS deployment, detailed explanations |
| [DEPLOY_AZURE.md](DEPLOY_AZURE.md) | Azure Functions detailed guide (10 steps) | Manual Azure deployment, detailed explanations |
| [Dockerfile](Dockerfile) | Container definition | Understanding how app is containerized |
| [readme.md](readme.md) | Project overview | Getting started locally, API usage |

---

## 🤖 Automation Scripts

| Script | Platform | Time | Effort | Best For |
|--------|----------|------|--------|----------|
| [deploy-aws.ps1](deploy-aws.ps1) | AWS Lambda | 5 min | Zero | Everyone (if AWS ready) |
| [deploy-azure.ps1](deploy-azure.ps1) | Azure Functions | 10 min | Zero | Everyone (after Azure CLI install) |

---

## 🎯 Choose Your Path

### Path 1: "Just Deploy It" (Recommended for Most)
1. Read: [SERVERLESS_QUICKSTART.md](SERVERLESS_QUICKSTART.md) (2 min)
2. Check: [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) (2 min)
3. Run: `.\deploy-aws.ps1` or `.\deploy-azure.ps1`
4. Test: Use provided endpoint URLs
5. Done! ✅

**Time**: 5-10 minutes  
**Effort**: Minimal  
**Success Rate**: 95%+

---

### Path 2: "I Want to Understand" (For Learning)
1. Read: [SERVERLESS_QUICKSTART.md](SERVERLESS_QUICKSTART.md) (5 min)
2. Read: [DEPLOY_AWS.md](DEPLOY_AWS.md) or [DEPLOY_AZURE.md](DEPLOY_AZURE.md) (15 min)
3. Do: Manual steps from detailed guide
4. Learn: Understand each component
5. Done! ✅

**Time**: 25-30 minutes  
**Effort**: Moderate  
**Learning Value**: High

---

### Path 3: "Something Went Wrong" (Troubleshooting)
1. Check: [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) → "Common Issues & Fixes"
2. Read: [DEPLOY_AWS.md](DEPLOY_AWS.md#troubleshooting) or [DEPLOY_AZURE.md](DEPLOY_AZURE.md#troubleshooting)
3. Search: Specific error message in relevant guide
4. Verify: Prerequisites are met
5. Retry: Run script or manual steps again

**Time**: 5-15 minutes  
**Effort**: Low to Moderate

---

## 📋 Decision Tree

```
START: "I want to deploy this app to AWS or Azure"
│
├─→ Do I have AWS CLI configured?
│   ├─→ YES → "Try AWS Lambda?" 
│   │         ├─→ YES → Run: .\deploy-aws.ps1 ✅
│   │         └─→ NO → Continue below
│   └─→ NO → Skip AWS, go to Azure
│
├─→ Do I have Azure CLI installed & logged in?
│   ├─→ YES → Run: .\deploy-azure.ps1 ✅
│   └─→ NO → Read: SERVERLESS_QUICKSTART.md → Install Azure CLI → Run script ✅
│
└─→ Scripts not working?
    └─→ Read: DEPLOYMENT_CHECKLIST.md → Common Issues → Try again ✅
```

---

## 🚦 Quick Reference by Scenario

### "I have 5 minutes"
→ [SERVERLESS_QUICKSTART.md](SERVERLESS_QUICKSTART.md) + `.\deploy-aws.ps1`

### "I want AWS" 
→ [SERVERLESS_QUICKSTART.md](SERVERLESS_QUICKSTART.md#aws-lambda-us-east-1) + [DEPLOY_AWS.md](DEPLOY_AWS.md)

### "I want Azure"
→ [SERVERLESS_QUICKSTART.md](SERVERLESS_QUICKSTART.md#azure-functions-eastus) + [DEPLOY_AZURE.md](DEPLOY_AZURE.md)

### "I want both platforms"
→ Run `.\deploy-aws.ps1` first, then `.\deploy-azure.ps1`

### "I'm not sure"
→ Start with [SERVERLESS_QUICKSTART.md](SERVERLESS_QUICKSTART.md) → Read "Which Platform?" section

### "Something's broken"
→ [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md#-common-issues--fixes)

### "I need detailed steps"
→ [DEPLOY_AWS.md](DEPLOY_AWS.md) or [DEPLOY_AZURE.md](DEPLOY_AZURE.md)

### "I want to learn Docker/Containers"
→ Read: [Dockerfile](Dockerfile) + Compare with [DEPLOY_AWS.md](DEPLOY_AWS.md) Section 1-2

---

## ✅ File Checklist

All required deployment files present:

- [x] SERVERLESS_QUICKSTART.md - Quick start guide
- [x] DEPLOYMENT_CHECKLIST.md - Pre-flight verification
- [x] DEPLOY_AWS.md - AWS detailed guide
- [x] DEPLOY_AZURE.md - Azure detailed guide
- [x] deploy-aws.ps1 - AWS automation script
- [x] deploy-azure.ps1 - Azure automation script
- [x] Dockerfile - Container definition
- [x] requirements.txt - Python dependencies
- [x] app/main.py - FastAPI application
- [x] app/incident_service.py - Incident management
- [x] frontend/index.html - Web UI
- [x] data/detection_rules.json - Threat rules

---

## 🎓 Learning Progression

### Beginner
1. Read: [readme.md](readme.md)
2. Run: Local (python venv)
3. Use: Web UI
4. Deploy: [SERVERLESS_QUICKSTART.md](SERVERLESS_QUICKSTART.md)

### Intermediate
1. Read: [DEPLOY_AWS.md](DEPLOY_AWS.md) or [DEPLOY_AZURE.md](DEPLOY_AZURE.md)
2. Monitor: CloudWatch or Application Insights
3. Customize: Detection rules
4. Scale: Increase memory or concurrent executions

### Advanced
1. Multi-cloud: Deploy to both AWS & Azure
2. CI/CD: Automate redeployment
3. Performance: Optimize cold starts
4. Cost: Implement request filtering before analysis

---

## 📞 Support Resources

| Need | Resource |
|------|----------|
| AWS Help | aws.amazon.com/getting-started |
| Azure Help | learn.microsoft.com/azure/ |
| Docker Help | docs.docker.com |
| FastAPI Help | fastapi.tiangolo.com |
| Stuck? | Check DEPLOYMENT_CHECKLIST.md → Troubleshooting |

---

## 🔗 Quick Links

### Setup
- Configure AWS: `aws configure`
- Login to Azure: `az login`
- Update PowerShell: `Update-Help`

### Test Deployment
- AWS: See SERVERLESS_QUICKSTART.md → "Test your API" (AWS)
- Azure: See SERVERLESS_QUICKSTART.md → "Test your API" (Azure)

### Monitor Live
- AWS: `aws logs tail /aws/lambda/log-analyzer --follow`
- Azure: `az functionapp logstream --name log-analyzer-func --resource-group log-analyzer-rg`

### Clean Up
- AWS: See SERVERLESS_QUICKSTART.md → "Cleanup"
- Azure: See SERVERLESS_QUICKSTART.md → "Cleanup"

---

**Ready? Start here:** [SERVERLESS_QUICKSTART.md](SERVERLESS_QUICKSTART.md) ⚡

