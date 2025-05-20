#!/bin/bash
# deploy.sh - Script to deploy the TechTranslator CloudFormation stacks

set -e  # Exit immediately if a command exits with a non-zero status

# Disable AWS CLI pager to prevent interactive less
export AWS_PAGER=""

# Configuration
PROJECT_NAME="TechTranslator"
REGION="us-east-1"  # Use the region that's available in your AWS Academy Lab
STACK_NAME_PREFIX="tech-translator"
LAMBDA_CODE_BUCKET="tech-translator-lambda-code"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting deployment of $PROJECT_NAME infrastructure...${NC}"

# Package Lambda functions
echo -e "${YELLOW}Packaging Lambda functions...${NC}"
./package-lambda.sh

# 1. Deploy S3 resources
echo -e "${YELLOW}Deploying S3 resources...${NC}"
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

echo "Website Bucket Name: $S3_BUCKET_NAME"

# 2. Deploy DynamoDB resources
echo -e "${YELLOW}Deploying DynamoDB tables...${NC}"
aws cloudformation deploy \
  --template-file infrastructure/dynamodb.yaml \
  --stack-name "${STACK_NAME_PREFIX}-dynamodb" \
  --parameter-overrides ProjectName=$PROJECT_NAME \
  --region $REGION

# 3. Deploy Cognito resources
echo -e "${YELLOW}Deploying Cognito authentication resources...${NC}"
aws cloudformation deploy \
  --template-file infrastructure/cognito.yaml \
  --stack-name "${STACK_NAME_PREFIX}-cognito" \
  --parameter-overrides \
    ProjectName=$PROJECT_NAME \
    S3StackName="${STACK_NAME_PREFIX}-s3" \
    WebsiteBucketName=$S3_BUCKET_NAME \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region $REGION

# Get Cognito resource IDs for future reference
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

echo "Cognito User Pool ID: $USER_POOL_ID"
echo "Cognito User Pool Client ID: $USER_POOL_CLIENT_ID"

# 4. Deploy Lambda functions
echo -e "${YELLOW}Deploying Lambda functions...${NC}"
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

# 5. Deploy API Gateway
echo -e "${YELLOW}Deploying API Gateway...${NC}"
aws cloudformation deploy \
  --template-file infrastructure/api-gateway.yaml \
  --stack-name "${STACK_NAME_PREFIX}-api" \
  --parameter-overrides \
    ProjectName=$PROJECT_NAME \
    LambdaStackName="${STACK_NAME_PREFIX}-lambda" \
    CognitoStackName="${STACK_NAME_PREFIX}-cognito" \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region $REGION

# Get API Gateway URL
API_URL=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME_PREFIX}-api" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayUrl'].OutputValue" \
  --output text)

echo -e "${GREEN}All resources for $PROJECT_NAME have been deployed successfully!${NC}"
echo -e "S3 Website URL: http://$S3_BUCKET_NAME.s3-website-$REGION.amazonaws.com"
echo -e "API Gateway URL: $API_URL"
echo -e "Cognito User Pool ID: $USER_POOL_ID"
echo -e "Cognito User Pool Client ID: $USER_POOL_CLIENT_ID"