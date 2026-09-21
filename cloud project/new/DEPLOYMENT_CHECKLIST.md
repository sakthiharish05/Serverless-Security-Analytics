# ✅ Deployment Pre-Flight Checklist

Use this checklist to verify everything is ready before deploying.

---

## 🔵 Before Starting (All Platforms)

- [ ] Docker Desktop installed and running
  ```powershell
  docker --version
  docker ps
  ```

- [ ] Project folder opened in terminal/PowerShell
  ```powershell
  Get-Location
  # Should show: C:\Users\...\cloud project\new
  ```

- [ ] All project files present
  ```powershell
  Get-ChildItem -Path . -Include "Dockerfile", "requirements.txt", "app/main.py", "deploy-*.ps1"
  ```

---

## 🟢 AWS Lambda Deployment

### Prerequisites

- [ ] AWS CLI installed
  ```powershell
  aws --version
  ```

- [ ] AWS credentials configured
  ```powershell
  aws sts get-caller-identity
  # Should return your account info, not an error
  ```

- [ ] IAM permissions (your AWS user can):
  - [ ] Create ECR repositories
  - [ ] Push to ECR
  - [ ] Create Lambda functions
  - [ ] Create API Gateway
  - [ ] Create IAM roles

### Permissions Check
If you get access denied errors, your AWS user needs these policy permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:*",
        "lambda:*",
        "apigateway:*",
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:GetRole"
      ],
      "Resource": "*"
    }
  ]
}
```

### Ready to Deploy?

```powershell
# Run the deployment script
.\deploy-aws.ps1

# Or with custom parameters:
.\deploy-aws.ps1 -AwsRegion us-east-1 -MemorySize 1024
```

After deployment, test the endpoint:
```powershell
$url = "https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/"
$body = @{logs = "user login failed from 10.0.0.1"} | ConvertTo-Json
Invoke-RestMethod -Uri $url -Method POST -Body $body -ContentType 'application/json'
```

---

## 🟢 Azure Functions Deployment

### Prerequisites

- [ ] Azure account created (free tier available)
  - Go to: https://azure.microsoft.com/free

- [ ] Azure CLI installed
  ```powershell
  choco install azure-cli
  # OR
  scoop install azure-cli
  # Verify:
  az --version
  ```

- [ ] Logged into Azure
  ```powershell
  az login
  # Opens browser for authentication
  # Verify:
  az account show
  ```

- [ ] Azure subscription has:
  - [ ] Sufficient quota for resource groups (usually unlimited)
  - [ ] No blocking policies (check with your org)

### Free Tier Check

```powershell
# See your current usage
az account show --query name
az resource list --query "[].type" --output table
```

### Ready to Deploy?

```powershell
# Run the deployment script
.\deploy-azure.ps1

# Or with custom parameters:
.\deploy-azure.ps1 -ResourceGroup log-analyzer-rg -FunctionAppName log-analyzer-func
```

After deployment, test the endpoint:
```powershell
$url = "https://YOUR_FUNCTION_NAME.azurewebsites.net/api/analyze_logs"
$headers = @{'x-functions-key' = 'YOUR_FUNCTION_KEY'}
$body = @{logs = "user login failed from 10.0.0.1"} | ConvertTo-Json
Invoke-RestMethod -Uri $url -Method POST -Body $body -Headers $headers -ContentType 'application/json'
```

---

## 🟡 Docker Verification

```powershell
# Build local image to verify no errors
docker build -t log-analyzer:test .

# Should complete without errors
# Size should be ~200-300MB
docker images | grep log-analyzer
```

If build fails:
- [ ] Check Python version (3.9+): `python --version`
- [ ] Check requirements.txt is readable: `Get-Content requirements.txt`
- [ ] Check Dockerfile exists: `Get-ChildItem Dockerfile`

---

## 🟡 Network & Firewall

- [ ] Can pull from Docker Hub
  ```powershell
  docker pull python:3.10-slim
  ```

- [ ] Can reach AWS services (if AWS):
  ```powershell
  Invoke-RestMethod -Uri "https://sts.amazonaws.com" -Method GET
  ```

- [ ] Can reach Azure services (if Azure):
  ```powershell
  Invoke-RestMethod -Uri "https://management.azure.com" -Method GET
  ```

---

## 🟡 Disk Space

Verify enough disk space:
```powershell
# Check free space
Get-Volume | Where-Object {$_.DriveLetter -eq 'C'} | Select-Object SizeRemaining

# Should be > 10 GB
```

Docker images needed:
- Python 3.10-slim: ~150MB
- Built image: ~200-300MB
- Total: ~500MB needed

---

## ⚠️ Common Issues & Fixes

### Docker Build Fails

**Error**: `python: command not found`
```powershell
# Solution: Install Python 3.9+
python --version  # Should show 3.9, 3.10, 3.11, or later
```

**Error**: `pip: No module named pip`
```powershell
# Solution: Update Python
python -m ensurepip --upgrade
```

### AWS Errors

**Error**: `UnauthorizedOperation`
```powershell
# Solution: Check credentials
aws sts get-caller-identity
# If error, run: aws configure
```

**Error**: `RepositoryAlreadyExistsException`
```powershell
# Solution: Different repo name
.\deploy-aws.ps1 -FunctionName my-analyzer-v2
```

### Azure Errors

**Error**: `az: command not found`
```powershell
# Solution: Install and add to PATH
choco install azure-cli
# Restart PowerShell
```

**Error**: `Not authenticated`
```powershell
# Solution: Login again
az login
```

---

## ✅ Final Verification Checklist

### AWS

- [ ] Script completed without errors
- [ ] ECR repository created in us-east-1
- [ ] Lambda function exists and is active
- [ ] API Gateway endpoint provided
- [ ] Test request returns valid threat detection response
- [ ] CloudWatch logs show function execution

### Azure

- [ ] Script completed without errors
- [ ] Resource group created
- [ ] Container registry created and image pushed
- [ ] Function App created and running
- [ ] Function endpoint responds to requests
- [ ] Function key provided and working
- [ ] Application Insights available for monitoring

---

## 📞 Troubleshooting

If something fails:

1. **Read error message carefully** - Usually tells you exactly what failed
2. **Check the detailed guide**:
   - AWS: [DEPLOY_AWS.md](DEPLOY_AWS.md#troubleshooting)
   - Azure: [DEPLOY_AZURE.md](DEPLOY_AZURE.md#troubleshooting)
3. **Run diagnosis**:
   ```powershell
   docker --version
   aws --version
   az --version
   ```
4. **Check logs**:
   ```powershell
   # AWS
   aws logs tail /aws/lambda/log-analyzer --follow --region us-east-1
   
   # Azure
   az functionapp logstream --name log-analyzer-func --resource-group log-analyzer-rg
   ```

---

## 💡 Pro Tips

1. **Start with AWS** if new to cloud - simpler setup, same functionality
2. **Use free tier** to test before production deployment
3. **Monitor costs** - both have cost estimators in console
4. **Keep function keys safe** - don't commit to git
5. **Test with sample logs** from `detection_rules.json` comments

---

## 🚀 Next Steps After Deployment

1. ✅ Copy endpoint URL from script output
2. ✅ Test with sample logs (script provides examples)
3. ✅ Monitor first 24h for errors
4. ✅ Set up cost alerts (both platforms support this)
5. ✅ Document your endpoint URLs privately
6. ✅ Plan for incident.json backup strategy
7. ✅ Add custom detection rules as needed

