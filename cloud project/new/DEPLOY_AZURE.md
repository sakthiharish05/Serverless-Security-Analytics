# Azure Functions Deployment Guide

## Prerequisites

⚠️ Azure CLI not configured yet - we'll set it up  
✅ Docker installed  
⚠️ Azure subscription (create free account at https://azure.microsoft.com/free/)

---

## Step 1: Install & Configure Azure CLI

### Install Azure CLI

**Windows:**
```powershell
# Download and run installer
Start-Process https://aka.ms/installazurecliwindows

# Or using Chocolatey
choco install azure-cli

# Or using Scoop
scoop install azure-cli

# Verify installation
az --version
```

**PowerShell:**
```powershell
# Using PowerShell Package Manager
Install-Module -Name Az -Repository PSGallery -Force
```

### Login to Azure

```powershell
# Interactive login (opens browser)
az login

# Verify login
az account show
```

---

## Step 2: Create Resource Group & Container Registry

```powershell
# Set variables
$RESOURCE_GROUP = "log-analyzer-rg"
$LOCATION = "eastus"
$REGISTRY_NAME = "loganalyzerregistry"
$FUNCTION_APP_NAME = "log-analyzer-func"

# Create resource group
az group create `
    --name $RESOURCE_GROUP `
    --location $LOCATION

Write-Host "Resource group created: $RESOURCE_GROUP"

# Create Azure Container Registry
az acr create `
    --resource-group $RESOURCE_GROUP `
    --name $REGISTRY_NAME `
    --sku Basic `
    --admin-enabled true

Write-Host "ACR created: $REGISTRY_NAME"

# Get registry login credentials (keep these safe!)
$REGISTRY_PASSWORD = az acr credential show `
    --resource-group $RESOURCE_GROUP `
    --name $REGISTRY_NAME `
    --query "passwords[0].value" `
    --output tsv

$REGISTRY_USERNAME = az acr credential show `
    --resource-group $RESOURCE_GROUP `
    --name $REGISTRY_NAME `
    --query "username" `
    --output tsv

$REGISTRY_URL = "$REGISTRY_NAME.azurecr.io"

Write-Host "Registry URL: $REGISTRY_URL"
Write-Host "Username: $REGISTRY_USERNAME"
```

---

## Step 3: Build & Push Docker Image to ACR

```powershell
cd "C:\Users\garre\Downloads\cloud project\cloud project\new"

# Build image
docker build -t log-analyzer:latest .

# Login to ACR
az acr login --name $REGISTRY_NAME

# Tag image for ACR
$IMAGE_TAG = "$REGISTRY_URL/log-analyzer:latest"
docker tag log-analyzer:latest $IMAGE_TAG

# Push to ACR
docker push $IMAGE_TAG

Write-Host "Image pushed to: $IMAGE_TAG"

# Verify push
az acr repository list --name $REGISTRY_NAME --output table
```

---

## Step 4: Create Storage Account (Required for Functions)

```powershell
$STORAGE_ACCOUNT = "loganalyzerstorage"

# Create storage account (must be globally unique)
az storage account create `
    --name $STORAGE_ACCOUNT `
    --resource-group $RESOURCE_GROUP `
    --location $LOCATION `
    --sku Standard_LRS

Write-Host "Storage account created: $STORAGE_ACCOUNT"
```

---

## Step 5: Create Function App

### Option A: Using Console (Recommended for beginners)

1. Go to Azure Portal: https://portal.azure.com/
2. Search for "Function App" and click "Create"
3. **Basics Tab:**
   - Resource group: Select the one we created
   - Function App name: `log-analyzer-func`
   - Publish: `Docker Container`
   - OS: `Linux`
   - Plan: `Consumption (Serverless)`
4. **Docker Tab:**
   - Image source: `Azure Container Registry`
   - Registry: Select your registry
   - Image: `log-analyzer`
   - Tag: `latest`
5. Review and create

### Option B: Using Azure CLI

```powershell
# Create function app with container
az functionapp create `
    --name $FUNCTION_APP_NAME `
    --storage-account $STORAGE_ACCOUNT `
    --resource-group $RESOURCE_GROUP `
    --functions-version 4 `
    --runtime python `
    --runtime-version 3.10 `
    --deployment-container-image-name $IMAGE_TAG `
    --deployment-container-registry-url "https://$REGISTRY_URL" `
    --deployment-container-registry-username $REGISTRY_USERNAME `
    --deployment-container-registry-password $REGISTRY_PASSWORD

Write-Host "Function App created: $FUNCTION_APP_NAME"
```

---

## Step 6: Configure Function App Settings

```powershell
# Set environment variables (if needed)
az functionapp config appsettings set `
    --name $FUNCTION_APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --settings "WEBSITES_ENABLE_APP_SERVICE_STORAGE=false"

# Create HTTP trigger
az functionapp function show `
    --name $FUNCTION_APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --function-name 'HttpTrigger' `
    2>$null || Write-Host "Function will be created automatically from container"
```

---

## Step 7: Get Function URL

```powershell
# Get the function app URL
$FUNCTION_URL = az functionapp show `
    --name $FUNCTION_APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --query "defaultHostName" `
    --output tsv

Write-Host "Function URL: https://$FUNCTION_URL"

# Get function key for authentication (optional)
$FUNCTION_KEY = az functionapp keys list `
    --name $FUNCTION_APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --query "functionKeys.default" `
    --output tsv

Write-Host "Function Key: $FUNCTION_KEY"
```

---

## Step 8: Test Deployment

```powershell
# Get the analysis function URL
$ANALYZE_URL = "https://$FUNCTION_URL/api/analyze_logs"

# Test with logs
$body = @{logs = 'user login failed from 10.0.0.1'} | ConvertTo-Json

Invoke-RestMethod `
    -Uri $ANALYZE_URL `
    -Method POST `
    -ContentType 'application/json' `
    -Body $body `
    -Headers @{"x-functions-key" = $FUNCTION_KEY}
```

---

## Step 9: Monitor Function

```powershell
# View function logs in real-time
az functionapp logstream `
    --name $FUNCTION_APP_NAME `
    --resource-group $RESOURCE_GROUP

# Or in Azure Portal:
# 1. Go to Function App
# 2. Click "Monitor" in left sidebar
# 3. View invocations and performance metrics
```

---

## Step 10: Deploy Updates

When you update the code:

```powershell
# Rebuild image
docker build -t log-analyzer:latest .

# Push to ACR
docker push $IMAGE_TAG

# Restart function app (pulls latest image)
az functionapp restart `
    --name $FUNCTION_APP_NAME `
    --resource-group $RESOURCE_GROUP

Write-Host "Function app restarted with new image"
```

---

## Monitoring & Alerts

```powershell
# View function statistics
az functionapp show `
    --name $FUNCTION_APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --query "properties"

# View application insights (if enabled)
az monitor app-insights component show `
    --app $FUNCTION_APP_NAME `
    --resource-group $RESOURCE_GROUP `
    2>$null || Write-Host "Application Insights not configured"
```

---

## Cost Optimization

- **Plan**: Consumption (pay per execution)
- **Storage**: Billed separately (~$0.24/GB/month)
- **Estimated Cost**: ~FREE for < 1M monthly requests (free tier)
- **Premium option**: Premium plan for guaranteed performance

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Image push fails | Run `az acr login --name $REGISTRY_NAME` again |
| Function won't start | Check Application Insights/Monitor tab for errors |
| 502 Bad Gateway | Check logs with `az functionapp logstream` |
| Permission denied | Verify registry credentials: `az acr credential show` |
| Cold start slow | Consumption plan has ~5s first invocation |
| Authorization failed | Include function key in header: `x-functions-key` |

---

## Cleanup (Delete Resources)

```powershell
# Delete entire resource group (deletes everything)
az group delete --name $RESOURCE_GROUP --yes

# Or delete individual resources
az functionapp delete --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP
az acr delete --name $REGISTRY_NAME --resource-group $RESOURCE_GROUP
az storage account delete --name $STORAGE_ACCOUNT --resource-group $RESOURCE_GROUP
```
