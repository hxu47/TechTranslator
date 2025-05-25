#!/bin/bash
# deploy.sh - Script to deploy the TechTranslator CloudFormation stacks with Authentication and Monitoring

set -e  # Exit immediately if a command exits with a non-zero status

# Disable AWS CLI pager to prevent interactive less
export AWS_PAGER=""

# Configuration
PROJECT_NAME="TechTranslator"
REGION="us-east-1"  # Use the region that's available in your AWS Academy Lab
STACK_NAME_PREFIX="tech-translator"
LAMBDA_CODE_BUCKET="tech-translator-lambda-code"
ENABLE_AUTH="true"  # Set to "true" to enable authentication

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}🚀 Starting deployment of $PROJECT_NAME with Authentication, Monitoring & Security${NC}"
echo -e "${BLUE}================================================${NC}"

# 1. Deploy S3 resources
echo -e "${YELLOW}📦 Step 1/7: Deploying S3 resources...${NC}"
aws cloudformation deploy \
  --template-file infrastructure/s3.yaml \
  --stack-name "${STACK_NAME_PREFIX}-s3" \
  --parameter-overrides ProjectName=$PROJECT_NAME \
  --region $REGION

# Get the S3 bucket name from the S3 stack
S3_BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME_PREFIX}-s3" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='WebsiteBucketName'].OutputValue" \
  --output text)

echo -e "${GREEN}✅ S3 resources deployed${NC}"
echo -e "   Website Bucket: $S3_BUCKET_NAME"

# 2. Deploy DynamoDB resources
echo -e "${YELLOW}📦 Step 2/7: Deploying DynamoDB tables...${NC}"
aws cloudformation deploy \
  --template-file infrastructure/dynamodb.yaml \
  --stack-name "${STACK_NAME_PREFIX}-dynamodb" \
  --parameter-overrides ProjectName=$PROJECT_NAME \
  --region $REGION

echo -e "${GREEN}✅ DynamoDB tables deployed${NC}"

# 3. Deploy Cognito resources
echo -e "${YELLOW}📦 Step 3/7: Deploying Cognito authentication resources...${NC}"
aws cloudformation deploy \
  --template-file infrastructure/cognito.yaml \
  --stack-name "${STACK_NAME_PREFIX}-cognito" \
  --parameter-overrides \
    ProjectName=$PROJECT_NAME \
    S3StackName="${STACK_NAME_PREFIX}-s3" \
    WebsiteBucketName=$S3_BUCKET_NAME \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region $REGION

# Get Cognito resource IDs
USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME_PREFIX}-cognito" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" \
  --output text)

USER_POOL_CLIENT_ID=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME_PREFIX}-cognito" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='UserPoolClientId'].OutputValue" \
  --output text)

IDENTITY_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME_PREFIX}-cognito" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='IdentityPoolId'].OutputValue" \
  --output text)

echo -e "${GREEN}✅ Cognito authentication deployed${NC}"
echo -e "   User Pool ID: $USER_POOL_ID"
echo -e "   User Pool Client ID: $USER_POOL_CLIENT_ID"
echo -e "   Identity Pool ID: $IDENTITY_POOL_ID"

# 4. Create/check Lambda code bucket and upload Lambda code
echo -e "${YELLOW}📦 Step 4/7: Setting up Lambda code...${NC}"

# Check if the bucket exists
if aws s3api head-bucket --bucket $LAMBDA_CODE_BUCKET 2>/dev/null; then
  echo "Lambda code bucket already exists: $LAMBDA_CODE_BUCKET"
else
  echo "Creating Lambda code bucket: $LAMBDA_CODE_BUCKET"
  aws s3api create-bucket --bucket $LAMBDA_CODE_BUCKET --region $REGION
fi

# Package and upload Lambda code
echo -e "${YELLOW}🔧 Packaging Lambda functions...${NC}"
./package-lambda.sh

echo -e "${GREEN}✅ Lambda code packaged and uploaded${NC}"

# 5. Deploy Lambda functions
echo -e "${YELLOW}📦 Step 5/7: Deploying Lambda functions...${NC}"
aws cloudformation deploy \
  --template-file infrastructure/lambda.yaml \
  --stack-name "${STACK_NAME_PREFIX}-lambda" \
  --parameter-overrides \
    ProjectName=$PROJECT_NAME \
    S3StackName="${STACK_NAME_PREFIX}-s3" \
    DynamoDBStackName="${STACK_NAME_PREFIX}-dynamodb" \
    CognitoStackName="${STACK_NAME_PREFIX}-cognito" \
    LambdaCodeBucket=$LAMBDA_CODE_BUCKET \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region $REGION

echo -e "${GREEN}✅ Lambda functions deployed${NC}"

# 6. Deploy API Gateway with Authentication
echo -e "${YELLOW}📦 Step 6/9: Deploying API Gateway with Authentication...${NC}"
aws cloudformation deploy \
  --template-file infrastructure/api-gateway.yaml \
  --stack-name "${STACK_NAME_PREFIX}-api" \
  --parameter-overrides \
    ProjectName=$PROJECT_NAME \
    LambdaStackName="${STACK_NAME_PREFIX}-lambda" \
    CognitoStackName="${STACK_NAME_PREFIX}-cognito" \
    EnableAuthForQuery=$ENABLE_AUTH \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region $REGION

# Get API Gateway URL
API_URL=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME_PREFIX}-api" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayUrl'].OutputValue" \
  --output text)

echo -e "${GREEN}✅ API Gateway deployed with authentication${NC}"

# 7. NEW: Deploy WAF Protection
echo -e "${YELLOW}🛡️ Step 7/9: Deploying WAF security protection...${NC}"
aws cloudformation deploy \
  --template-file infrastructure/waf.yaml \
  --stack-name "${STACK_NAME_PREFIX}-waf" \
  --parameter-overrides \
    ProjectName=$PROJECT_NAME \
    ApiStackName="${STACK_NAME_PREFIX}-api" \
  --region $REGION

echo -e "${GREEN}✅ WAF protection deployed${NC}"

# 8. Deploy CloudWatch Monitoring and Governance
echo -e "${YELLOW}📊 Step 8/9: Deploying CloudWatch monitoring and governance...${NC}"
aws cloudformation deploy \
  --template-file infrastructure/cloudwatch.yaml \
  --stack-name "${STACK_NAME_PREFIX}-monitoring" \
  --parameter-overrides \
    ProjectName=$PROJECT_NAME \
    LambdaStackName="${STACK_NAME_PREFIX}-lambda" \
    ApiStackName="${STACK_NAME_PREFIX}-api" \
    DynamoDBStackName="${STACK_NAME_PREFIX}-dynamodb" \
  --region $REGION

# Get CloudWatch Dashboard URL
DASHBOARD_URL=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME_PREFIX}-monitoring" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='DashboardUrl'].OutputValue" \
  --output text)

echo -e "${GREEN}✅ CloudWatch monitoring deployed${NC}"
echo -e "   Dashboard URL: $DASHBOARD_URL"

# 8. Deploy frontend with configuration
echo -e "${YELLOW}🌐 Deploying frontend with authentication configuration...${NC}"
./upload-frontend.sh

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!${NC}"
echo -e "${BLUE}================================================${NC}"

echo -e "${YELLOW}📋 Deployment Summary:${NC}"
echo -e "   🌐 Website URL: http://$S3_BUCKET_NAME.s3-website-$REGION.amazonaws.com"
echo -e "   🔗 API Gateway URL: $API_URL"
echo -e "   📊 CloudWatch Dashboard: $DASHBOARD_URL"
echo -e "   🔐 Authentication: ${ENABLE_AUTH}"
echo -e "   👤 User Pool ID: $USER_POOL_ID"
echo -e "   📱 Client ID: $USER_POOL_CLIENT_ID"
echo -e "   🆔 Identity Pool ID: $IDENTITY_POOL_ID"

echo -e "${YELLOW}📊 Security & Monitoring Features:${NC}"
echo -e "   ✅ WAF Protection: Rate limiting, SQL injection, XSS protection"
echo -e "   ✅ CloudWatch Dashboard with Lambda, API Gateway, DynamoDB metrics"
echo -e "   ✅ CloudWatch Alarms for error rates and high latency"
echo -e "   ✅ Log retention policies for cost optimization"
echo -e "   ✅ Custom metrics for SageMaker endpoint health"

echo -e "${YELLOW}📝 Next Steps:${NC}"
echo -e "   1. 🧪 Test user registration and login at the website"
echo -e "   2. 📊 View monitoring dashboard: $DASHBOARD_URL"
echo -e "   3. 🤖 Deploy a SageMaker endpoint using the Jupyter notebook"
echo -e "   4. 🔄 Update Lambda with the SageMaker endpoint name:"
echo -e "      aws cloudformation update-stack \\"
echo -e "        --stack-name ${STACK_NAME_PREFIX}-lambda \\"
echo -e "        --use-previous-template \\"
echo -e "        --parameters ParameterKey=SageMakerEndpointName,ParameterValue=YOUR_ENDPOINT_NAME \\"
echo -e "        --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM"

# Check SageMaker endpoint status
echo -e "${YELLOW}🔍 Checking current SageMaker endpoint configuration...${NC}"
CURRENT_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME_PREFIX}-lambda" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='CurrentSageMakerEndpoint'].OutputValue" \
  --output text 2>/dev/null || echo "NOT_CONFIGURED")

if [ "$CURRENT_ENDPOINT" = "NOT_CONFIGURED" ] || [ "$CURRENT_ENDPOINT" = "PLACEHOLDER" ]; then
  echo -e "${RED}⚠️  WARNING: SageMaker endpoint not configured!${NC}"
  echo -e "   The app will show an error until you deploy and configure a SageMaker endpoint."
else
  echo -e "${GREEN}✅ SageMaker endpoint configured: $CURRENT_ENDPOINT${NC}"
fi

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}🚀 Your TechTranslator app with monitoring is ready!${NC}"
echo -e "${YELLOW}📸 For Milestone 2 screenshots, visit: $DASHBOARD_URL${NC}"
echo -e "${BLUE}================================================${NC}"