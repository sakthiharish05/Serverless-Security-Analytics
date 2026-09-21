# AWS Lambda Deployment Script (Automated)
# This script automates the entire deployment process

param(
    [string]$FunctionName = "log-analyzer",
    [string]$AwsRegion = "us-east-1",
    [int]$MemorySize = 1024,
    [int]$Timeout = 60
)

Write-Host "=== AWS Lambda Deployment ===" -ForegroundColor Green
Write-Host "Function: $FunctionName | Region: $AwsRegion | Memory: ${MemorySize}MB"
Write-Host ""

# Step 1: Build Docker image
Write-Host "[1/5] Building Docker image..." -ForegroundColor Cyan
docker build -t $FunctionName:latest .
if ($LASTEXITCODE -ne 0) { Write-Error "Docker build failed"; exit 1 }

# Step 2: Get AWS Account ID and create ECR repo
Write-Host "[2/5] Setting up ECR repository..." -ForegroundColor Cyan
$AWS_ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$ECR_REPO_NAME = $FunctionName
$ECR_URI = "$AWS_ACCOUNT_ID.dkr.ecr.$AwsRegion.amazonaws.com/$ECR_REPO_NAME:latest"

# Check if repo exists
$repo_exists = aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AwsRegion 2>$null
if (-not $repo_exists) {
    Write-Host "Creating ECR repository: $ECR_REPO_NAME"
    aws ecr create-repository --repository-name $ECR_REPO_NAME --region $AwsRegion | Out-Null
} else {
    Write-Host "ECR repository already exists"
}

# Step 3: Login and push to ECR
Write-Host "[3/5] Pushing image to ECR..." -ForegroundColor Cyan
aws ecr get-login-password --region $AwsRegion | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AwsRegion.amazonaws.com
docker tag $FunctionName:latest $ECR_URI
docker push $ECR_URI
Write-Host "Image pushed: $ECR_URI" -ForegroundColor Green

# Step 4: Create or update Lambda function
Write-Host "[4/5] Creating/updating Lambda function..." -ForegroundColor Cyan
$function_exists = aws lambda get-function --function-name $FunctionName --region $AwsRegion 2>$null

if ($function_exists) {
    Write-Host "Function exists, updating code..."
    aws lambda update-function-code `
        --function-name $FunctionName `
        --image-uri $ECR_URI `
        --region $AwsRegion | Out-Null
} else {
    Write-Host "Function doesn't exist, creating..."
    
    # Create IAM role first
    $ROLE_NAME = "$FunctionName-role"
    $trust_policy = @{
        Version = "2012-10-17"
        Statement = @(@{
            Effect = "Allow"
            Principal = @{ Service = "lambda.amazonaws.com" }
            Action = "sts:AssumeRole"
        })
    } | ConvertTo-Json
    
    $role_exists = aws iam get-role --role-name $ROLE_NAME 2>$null
    if (-not $role_exists) {
        Write-Host "Creating IAM role: $ROLE_NAME"
        aws iam create-role `
            --role-name $ROLE_NAME `
            --assume-role-policy-document $trust_policy | Out-Null
        Start-Sleep -Seconds 5  # Wait for role to be ready
    }
    
    $ROLE_ARN = aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text
    
    aws lambda create-function `
        --function-name $FunctionName `
        --role $ROLE_ARN `
        --code ImageUri=$ECR_URI `
        --package-type Image `
        --timeout $Timeout `
        --memory-size $MemorySize `
        --region $AwsRegion | Out-Null
}

# Update configuration
Write-Host "Configuring function..."
aws lambda update-function-configuration `
    --function-name $FunctionName `
    --timeout $Timeout `
    --memory-size $MemorySize `
    --region $AwsRegion | Out-Null

# Step 5: Create API Gateway (if needed)
Write-Host "[5/5] Setting up API Gateway..." -ForegroundColor Cyan
$API_NAME = "$FunctionName-api"

# Check if API exists
$api = aws apigateway get-rest-apis --region $AwsRegion --query "items[?name=='$API_NAME'].id" --output text

if ($api) {
    Write-Host "API Gateway already exists: $api"
} else {
    Write-Host "Creating API Gateway..."
    $api_response = aws apigateway create-rest-api `
        --name $API_NAME `
        --description "Log Analyzer API" `
        --region $AwsRegion | ConvertFrom-Json
    $api = $api_response.id
    
    # Grant API Gateway permission
    aws lambda add-permission `
        --function-name $FunctionName `
        --statement-id AllowAPIGateway `
        --action lambda:InvokeFunction `
        --principal apigateway.amazonaws.com `
        --region $AwsRegion 2>$null
}

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Green
Write-Host "AWS Account ID: $AWS_ACCOUNT_ID"
Write-Host "Region: $AwsRegion"
Write-Host "Function Name: $FunctionName"
Write-Host "ECR Image URI: $ECR_URI"
Write-Host "API ID: $api"
Write-Host ""
Write-Host "Test command:" -ForegroundColor Yellow
Write-Host "`$body = @{logs = 'user login failed from 10.0.0.1'} | ConvertTo-Json"
Write-Host "Invoke-RestMethod -Uri 'https://YOUR_API_ID.execute-api.$AwsRegion.amazonaws.com/prod/' -Method POST -Body `$body"
Write-Host ""
Write-Host "View logs:" -ForegroundColor Yellow
Write-Host "aws logs tail /aws/lambda/$FunctionName --follow --region $AwsRegion"
