# AWS Lambda Deployment Guide

## Prerequisites

✅ AWS CLI configured with credentials  
✅ Docker installed  
✅ jq (optional, for parsing JSON)

---

## Step 1: Build Docker Image Locally

```powershell
cd "C:\Users\garre\Downloads\cloud project\cloud project\new"

# Build the image
docker build -t log-analyzer:latest .

# Test locally (optional)
docker run -p 8000:80 log-analyzer:latest
# Visit http://localhost:8000 to verify
```

---

## Step 2: Create ECR Repository

```powershell
# Set variables
$AWS_ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$AWS_REGION = "us-east-1"
$ECR_REPO_NAME = "log-analyzer"

# Create ECR repository
aws ecr create-repository `
    --repository-name $ECR_REPO_NAME `
    --region $AWS_REGION

# Output will show the repository URI (save this)
$ECR_URI = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest"

Write-Host "ECR URI: $ECR_URI"
```

---

## Step 3: Push Image to ECR

```powershell
# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Tag image for ECR
docker tag log-analyzer:latest $ECR_URI

# Push to ECR
docker push $ECR_URI

Write-Host "Image pushed to: $ECR_URI"
```

---

## Step 4: Create Lambda Function

**Option A: Using Console**
1. Go to AWS Lambda Console: https://console.aws.amazon.com/lambda/
2. Click "Create function"
3. Choose "Container image"
4. Enter function name: `log-analyzer`
5. Paste ECR URI: `123456789.dkr.ecr.us-east-1.amazonaws.com/log-analyzer:latest`
6. Set memory: 512 MB (or higher)
7. Set timeout: 30 seconds
8. Click "Create function"
9. Once created, go to "Configuration" → "General configuration"
10. Change timeout to 60 seconds (for large logs)
11. Increase memory to 1024 MB for better performance

**Option B: Using AWS CLI**
```powershell
# Create IAM role for Lambda (if not exists)
$ROLE_NAME = "log-analyzer-lambda-role"
$TRUST_POLICY = @{
    Version = "2012-10-17"
    Statement = @(@{
        Effect = "Allow"
        Principal = @{ Service = "lambda.amazonaws.com" }
        Action = "sts:AssumeRole"
    })
} | ConvertTo-Json

# Create role
aws iam create-role `
    --role-name $ROLE_NAME `
    --assume-role-policy-document $TRUST_POLICY `
    --region $AWS_REGION

$ROLE_ARN = aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text

# Create Lambda function
aws lambda create-function `
    --function-name log-analyzer `
    --role $ROLE_ARN `
    --code ImageUri=$ECR_URI `
    --package-type Image `
    --timeout 60 `
    --memory-size 1024 `
    --region $AWS_REGION
```

---

## Step 5: Create API Gateway Trigger

**Option A: Using Console**
1. In Lambda function, go to "Add trigger"
2. Select "API Gateway"
3. Select "Create a new REST API"
4. Security: "OPEN" (or configure CORS/Auth as needed)
5. Click "Add"
6. Copy the API endpoint URL

**Option B: Using AWS CLI**
```powershell
# Create API Gateway
$API_NAME = "log-analyzer-api"
$API = aws apigateway create-rest-api `
    --name $API_NAME `
    --description "Log Analyzer API" `
    --region $AWS_REGION | ConvertFrom-Json

$API_ID = $API.id
$ROOT_ID = aws apigateway get-resources `
    --rest-api-id $API_ID `
    --region $AWS_REGION | ConvertFrom-Json | Select-Object -ExpandProperty items | Where-Object path -eq "/" | Select-Object -ExpandProperty id

# Create POST method
aws apigateway put-method `
    --rest-api-id $API_ID `
    --resource-id $ROOT_ID `
    --http-method POST `
    --authorization-type NONE `
    --region $AWS_REGION

# Grant API Gateway permission to invoke Lambda
aws lambda add-permission `
    --function-name log-analyzer `
    --statement-id AllowAPIGateway `
    --action lambda:InvokeFunction `
    --principal apigateway.amazonaws.com `
    --region $AWS_REGION

Write-Host "API Gateway ID: $API_ID"
```

---

## Step 6: Verify Deployment

```powershell
# Get Lambda function details
aws lambda get-function --function-name log-analyzer --region $AWS_REGION

# Get API Gateway URL
$API_ENDPOINT = "https://$API_ID.execute-api.$AWS_REGION.amazonaws.com/prod"

# Test the API
$body = @{logs = 'user login failed from 10.0.0.1'} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "$($API_ENDPOINT)/" `
    -Method POST `
    -ContentType 'application/json' `
    -Body $body
```

---

## Step 7: Deploy Updates

When you update the code:

```powershell
# Rebuild image
docker build -t log-analyzer:latest .

# Push to ECR
docker push $ECR_URI

# Update Lambda function
aws lambda update-function-code `
    --function-name log-analyzer `
    --image-uri $ECR_URI `
    --region $AWS_REGION
```

---

## Monitoring & Logs

```powershell
# View CloudWatch logs
aws logs tail /aws/lambda/log-analyzer --follow --region $AWS_REGION

# Get function metrics
aws cloudwatch get-metric-statistics `
    --namespace AWS/Lambda `
    --metric-name Duration `
    --dimensions Name=FunctionName,Value=log-analyzer `
    --start-time (Get-Date).AddHours(-1) `
    --end-time (Get-Date) `
    --period 300 `
    --statistics Average,Maximum `
    --region $AWS_REGION
```

---

## Cost Optimization

- **Memory**: Start with 512 MB, increase if timeouts occur
- **Timeout**: 60 seconds is sufficient for 50MB logs
- **Provisioned Concurrency**: Not needed unless expecting >1000 concurrent requests
- **Estimated Cost**: ~$0.20 per 1M requests (free tier: 1M requests/month)

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Image push fails | Run `aws ecr get-login-password ...` again |
| Lambda timeout | Increase timeout in Configuration, use larger memory |
| API 502 error | Check CloudWatch logs: `aws logs tail /aws/lambda/log-analyzer` |
| High latency | Cold start: Lambda needs ~5s first invocation, then <1s |
| Permission denied | Verify IAM role has correct permissions |
