# Azure Functions Deployment Script (Automated)
# This script automates the entire Azure deployment process

param(
    [string]$ResourceGroup = "log-analyzer-rg",
    [string]$Location = "eastus",
    [string]$FunctionAppName = "log-analyzer-func",
    [string]$RegistryName = "loganalyzerregistry"
)

Write-Host "=== Azure Functions Deployment ===" -ForegroundColor Green
Write-Host "Resource Group: $ResourceGroup"
Write-Host "Location: $Location"
Write-Host "Function App: $FunctionAppName"
Write-Host "Registry: $RegistryName"
Write-Host ""

# Step 0: Check Azure CLI
Write-Host "[0/7] Checking Azure CLI installation..." -ForegroundColor Cyan
try {
    $cli_version = az --version 2>$null | Select-Object -First 1
    Write-Host "Azure CLI version: $cli_version"
} catch {
    Write-Error "Azure CLI not found. Run: choco install azure-cli (or scoop install azure-cli)"
    exit 1
}

# Step 1: Login to Azure
Write-Host "[1/7] Checking Azure login..." -ForegroundColor Cyan
$current_user = az account show 2>$null
if (-not $current_user) {
    Write-Host "Not logged in, launching browser..."
    az login
}
$subscription = (az account show | ConvertFrom-Json).name
Write-Host "Logged in as: $subscription"

# Step 2: Create/Check Resource Group
Write-Host "[2/7] Setting up resource group..." -ForegroundColor Cyan
$rg_exists = az group exists --name $ResourceGroup
if ($rg_exists -eq "false") {
    Write-Host "Creating resource group: $ResourceGroup"
    az group create --name $ResourceGroup --location $Location | Out-Null
} else {
    Write-Host "Resource group already exists"
}

# Step 3: Create/Check Container Registry
Write-Host "[3/7] Setting up container registry..." -ForegroundColor Cyan
$registry_exists = az acr exists --name $RegistryName 2>$null | ConvertFrom-Json
if (-not $registry_exists) {
    Write-Host "Creating container registry: $RegistryName"
    az acr create `
        --resource-group $ResourceGroup `
        --name $RegistryName `
        --sku Basic `
        --admin-enabled true | Out-Null
}

# Get registry credentials
$REGISTRY_PASSWORD = az acr credential show `
    --resource-group $ResourceGroup `
    --name $RegistryName `
    --query "passwords[0].value" `
    --output tsv

$REGISTRY_USERNAME = az acr credential show `
    --resource-group $ResourceGroup `
    --name $RegistryName `
    --query "username" `
    --output tsv

$REGISTRY_URL = "$RegistryName.azurecr.io"
Write-Host "Registry: $REGISTRY_URL"

# Step 4: Build and push Docker image
Write-Host "[4/7] Building and pushing Docker image..." -ForegroundColor Cyan
docker build -t log-analyzer:latest .
if ($LASTEXITCODE -ne 0) { Write-Error "Docker build failed"; exit 1 }

Write-Host "Logging into registry..."
az acr login --name $RegistryName --username $REGISTRY_USERNAME --password $REGISTRY_PASSWORD

$IMAGE_TAG = "$REGISTRY_URL/log-analyzer:latest"
Write-Host "Tagging image: $IMAGE_TAG"
docker tag log-analyzer:latest $IMAGE_TAG

Write-Host "Pushing image to ACR..."
docker push $IMAGE_TAG
Write-Host "Image pushed successfully" -ForegroundColor Green

# Step 5: Create Storage Account
Write-Host "[5/7] Creating storage account..." -ForegroundColor Cyan
$STORAGE_ACCOUNT = "storage$(Get-Random -Minimum 100000 -Maximum 999999)"
$storage_exists = az storage account show --name $STORAGE_ACCOUNT --resource-group $ResourceGroup 2>$null
if (-not $storage_exists) {
    Write-Host "Creating storage account: $STORAGE_ACCOUNT"
    az storage account create `
        --name $STORAGE_ACCOUNT `
        --resource-group $ResourceGroup `
        --location $Location `
        --sku Standard_LRS | Out-Null
}

# Step 6: Create Function App
Write-Host "[6/7] Setting up Function App..." -ForegroundColor Cyan
$func_exists = az functionapp show --name $FunctionAppName --resource-group $ResourceGroup 2>$null
if ($func_exists) {
    Write-Host "Function App already exists, updating configuration..."
    az functionapp config container set `
        --name $FunctionAppName `
        --resource-group $ResourceGroup `
        --image-name $IMAGE_TAG `
        --docker-registry-server-url "https://$REGISTRY_URL" `
        --docker-registry-server-user $REGISTRY_USERNAME `
        --docker-registry-server-password $REGISTRY_PASSWORD | Out-Null
} else {
    Write-Host "Creating Function App: $FunctionAppName"
    az functionapp create `
        --name $FunctionAppName `
        --storage-account $STORAGE_ACCOUNT `
        --resource-group $ResourceGroup `
        --functions-version 4 `
        --runtime python `
        --runtime-version 3.10 `
        --deployment-container-image-name $IMAGE_TAG `
        --deployment-container-registry-url "https://$REGISTRY_URL" `
        --deployment-container-registry-username $REGISTRY_USERNAME `
        --deployment-container-registry-password $REGISTRY_PASSWORD | Out-Null
}

# Step 7: Get URLs and keys
Write-Host "[7/7] Finalizing..." -ForegroundColor Cyan
$FUNCTION_URL = az functionapp show `
    --name $FunctionAppName `
    --resource-group $ResourceGroup `
    --query "defaultHostName" `
    --output tsv

$FUNCTION_KEY = az functionapp keys list `
    --name $FunctionAppName `
    --resource-group $ResourceGroup `
    --query "functionKeys.default" `
    --output tsv

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Green
Write-Host "Resource Group: $ResourceGroup"
Write-Host "Location: $Location"
Write-Host "Function App URL: https://$FUNCTION_URL"
Write-Host "Function Key: $FUNCTION_KEY"
Write-Host "Registry: $REGISTRY_URL"
Write-Host ""
Write-Host "Test command:" -ForegroundColor Yellow
Write-Host "`$headers = @{ 'x-functions-key' = '$FUNCTION_KEY' }"
Write-Host "`$body = @{logs = 'user login failed from 10.0.0.1'} | ConvertTo-Json"
Write-Host "Invoke-RestMethod -Uri 'https://$FUNCTION_URL/api/analyze_logs' -Method POST -Body `$body -Headers `$headers"
Write-Host ""
Write-Host "View logs in real-time:" -ForegroundColor Yellow
Write-Host "az functionapp logstream --name $FunctionAppName --resource-group $ResourceGroup"
Write-Host ""
Write-Host "To delete all resources:" -ForegroundColor Yellow
Write-Host "az group delete --name $ResourceGroup --yes"
