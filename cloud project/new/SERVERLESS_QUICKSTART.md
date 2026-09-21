# 🚀 Quick Serverless Deployment Guide

Choose your platform and follow the **Fastest Path** below.

---

## 📋 AWS Lambda (us-east-1)

### ⚡ Fastest Path (5 minutes)

```powershell
# 1. Prerequisite: AWS CLI configured
aws sts get-caller-identity

# 2. Run deployment script
.\deploy-aws.ps1

# 3. Wait for completion (~3-5 minutes)
# Script will output API endpoint URL

# 4. Test your API
$body = @{logs = 'user login failed from 10.0.0.1'} | ConvertTo-Json
Invoke-RestMethod -Uri "https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/" `
    -Method POST -Body $body -ContentType 'application/json'
```

### 📖 Detailed Guide
See: [DEPLOY_AWS.md](DEPLOY_AWS.md)

### ✅ What the script does:
1. ✅ Builds Docker image
2. ✅ Creates ECR repository
3. ✅ Pushes image to ECR
4. ✅ Creates/updates Lambda function
5. ✅ Sets up API Gateway trigger
6. ✅ Outputs endpoint URL

### 💰 Cost
- **Free Tier**: 1M requests/month
- **Overage**: ~$0.20 per 1M requests
- **No charge** for storage in free tier

---

## ☁️ Azure Functions (eastus)

### ⚡ Fastest Path (10 minutes)

```powershell
# 1. Install Azure CLI if needed
choco install azure-cli

# 2. Login to Azure (opens browser)
az login

# 3. Run deployment script
.\deploy-azure.ps1

# 4. Wait for completion (~7-10 minutes)
# Script will output function endpoint URL

# 5. Test your API (use the function key from output)
$headers = @{ 'x-functions-key' = 'YOUR_FUNCTION_KEY' }
$body = @{logs = 'user login failed from 10.0.0.1'} | ConvertTo-Json
Invoke-RestMethod -Uri "https://YOUR_FUNCTION_NAME.azurewebsites.net/api/analyze_logs" `
    -Method POST -Body $body -Headers $headers -ContentType 'application/json'
```

### 📖 Detailed Guide
See: [DEPLOY_AZURE.md](DEPLOY_AZURE.md)

### ✅ What the script does:
1. ✅ Creates resource group
2. ✅ Creates container registry
3. ✅ Builds & pushes Docker image
4. ✅ Creates storage account
5. ✅ Creates Function App
6. ✅ Outputs endpoint URL & function key

### 💰 Cost
- **Free Tier**: 1M monthly requests + 400,000 GB-seconds
- **Consumption Plan**: Pay per execution (~FREE for typical usage)
- **Storage**: ~$0.24/GB/month

---

## 🔧 Manual Steps (If Scripts Don't Work)

### AWS Lambda

#### 1. Build & Push
```powershell
docker build -t log-analyzer:latest .

# Get account ID
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text

# Create ECR repo
aws ecr create-repository --repository-name log-analyzer --region us-east-1

# Login and push
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
docker tag log-analyzer:latest $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/log-analyzer:latest
docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/log-analyzer:latest
```

#### 2. Lambda Console
1. Go to https://console.aws.amazon.com/lambda/
2. Create Function → Container Image
3. Image URI: `YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/log-analyzer:latest`
4. Memory: 1024 MB, Timeout: 60s
5. Add API Gateway trigger

---

### Azure Functions

#### 1. Setup
```powershell
# Install & login
az login

# Create resource group
az group create --name log-analyzer-rg --location eastus

# Create registry
az acr create --resource-group log-analyzer-rg --name loganalyzerregistry --sku Basic
```

#### 2. Build & Push
```powershell
docker build -t log-analyzer:latest .

az acr login --name loganalyzerregistry
docker tag log-analyzer:latest loganalyzerregistry.azurecr.io/log-analyzer:latest
docker push loganalyzerregistry.azurecr.io/log-analyzer:latest
```

#### 3. Function App Console
1. Go to https://portal.azure.com/
2. Create Function App
3. Docker Container → Select image from registry
4. Configure settings
5. Deploy

---

## 🎯 Which Platform?

| Feature | AWS | Azure |
|---------|-----|-------|
| **Setup Time** | 5 min | 10 min |
| **Free Tier** | 1M requests | 1M requests |
| **Cold Start** | ~5s (first) | ~5s (first) |
| **Pricing** | $0.20/1M | Usually FREE |
| **Auto-scaling** | Instant | Instant |
| **Monitoring** | CloudWatch | Application Insights |
| **Recommended for** | Production | Learning/Dev |

**Recommendation**: Start with **AWS** (faster setup), add Azure later if needed.

---

## ✅ Verify Deployment

### AWS
```powershell
# Check Lambda function
aws lambda get-function --function-name log-analyzer --region us-east-1

# View logs
aws logs tail /aws/lambda/log-analyzer --follow --region us-east-1

# Invoke directly
aws lambda invoke --function-name log-analyzer --region us-east-1 response.json
cat response.json
```

### Azure
```powershell
# Check Function App
az functionapp show --name log-analyzer-func --resource-group log-analyzer-rg

# Stream logs
az functionapp logstream --name log-analyzer-func --resource-group log-analyzer-rg

# Monitor
az monitor app-insights events show --app log-analyzer-func --resource-group log-analyzer-rg
```

---

## 🔄 Update After Changes

### AWS
```powershell
docker build -t log-analyzer:latest .
docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/log-analyzer:latest
aws lambda update-function-code --function-name log-analyzer --image-uri $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/log-analyzer:latest --region us-east-1
```

### Azure
```powershell
docker build -t log-analyzer:latest .
docker push loganalyzerregistry.azurecr.io/log-analyzer:latest
az functionapp restart --name log-analyzer-func --resource-group log-analyzer-rg
```

---

## 🧹 Cleanup

### AWS (Delete everything)
```powershell
# Delete Lambda
aws lambda delete-function --function-name log-analyzer --region us-east-1

# Delete ECR repo
aws ecr delete-repository --repository-name log-analyzer --region us-east-1 --force

# Delete IAM role
aws iam delete-role --role-name log-analyzer-role
```

### Azure (Delete everything)
```powershell
# Delete entire resource group
az group delete --name log-analyzer-rg --yes
```

---

## 🚨 Troubleshooting

| Problem | Solution |
|---------|----------|
| Docker not found | Install Docker: https://www.docker.com/products/docker-desktop |
| AWS CLI not configured | Run `aws configure` and enter credentials |
| Azure not logged in | Run `az login` (opens browser) |
| Image push fails | Verify registry login: `aws ecr get-login-password...` or `az acr login` |
| Lambda timeout | Increase timeout in Configuration (max 15 minutes) |
| Function returns 502 | Check CloudWatch/Application Insights logs |
| High latency | Cold starts are normal (~5s first request), ~100ms after |

---

## 📊 Performance Tips

1. **Memory**: Start with 512MB, increase if slow
2. **Timeout**: 60 seconds is plenty for 50MB logs
3. **Concurrency**: Both platforms auto-scale
4. **Cost**: Barely noticeable unless 10M+ monthly requests

---

## 🎓 Next Steps

1. **Monitor Production**: Set up alerts for errors
2. **Add Custom Rules**: Edit `data/detection_rules.json`
3. **Enable Logging**: CloudWatch (AWS) or Application Insights (Azure)
4. **Scale Up**: Add more instances if needed (auto-scaling handles this)
5. **Backup**: Both platforms store function code, keep incidents.json backed up

