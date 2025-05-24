#!/bin/bash
# upload-frontend.sh - Script to upload frontend to S3

set -e  # Exit immediately if a command exits with a non-zero status

# Configuration
REGION="us-east-1"
STACK_NAME_PREFIX="tech-translator"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get S3 bucket name from CloudFormation stack
S3_BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME_PREFIX}-s3" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='WebsiteBucketName'].OutputValue" \
  --output text)

# Get API Gateway URL from CloudFormation stack
API_URL=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME_PREFIX}-api" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayUrl'].OutputValue" \
  --output text)

# Get Cognito User Pool ID and Client ID from CloudFormation stack
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

echo -e "${YELLOW}Uploading frontend to S3 bucket: $S3_BUCKET_NAME${NC}"
echo -e "API URL: $API_URL"
echo -e "User Pool ID: $USER_POOL_ID"
echo -e "User Pool Client ID: $USER_POOL_CLIENT_ID"

# Create a temporary directory for processing
TEMP_DIR=$(mktemp -d)
echo -e "Using temporary directory: $TEMP_DIR"

# Copy frontend files to temporary directory
cp -r frontend/public/* $TEMP_DIR/
mkdir -p $TEMP_DIR/src/css
mkdir -p $TEMP_DIR/src/js
mkdir -p $TEMP_DIR/src/assets
cp frontend/src/css/styles.css $TEMP_DIR/src/css/
cp frontend/src/js/*.js $TEMP_DIR/src/js/

# Replace placeholder values in JavaScript files
# Use different delimiter for sed to avoid issues with URLs containing slashes
sed -i.bak "s|YOUR_API_GATEWAY_URL|$API_URL|g" $TEMP_DIR/src/js/api.js
sed -i.bak "s|YOUR_USER_POOL_ID|$USER_POOL_ID|g" $TEMP_DIR/src/js/auth.js
sed -i.bak "s|YOUR_CLIENT_ID|$USER_POOL_CLIENT_ID|g" $TEMP_DIR/src/js/auth.js

# Remove backup files
rm $TEMP_DIR/src/js/*.bak

# Upload files to S3
echo -e "${YELLOW}Uploading files to S3...${NC}"
aws s3 sync $TEMP_DIR/ s3://$S3_BUCKET_NAME/ --delete

# Clean up temporary directory
rm -rf $TEMP_DIR

echo -e "${GREEN}Frontend uploaded successfully!${NC}"
echo -e "Website URL: http://$S3_BUCKET_NAME.s3-website-$REGION.amazonaws.com"

# Display current SageMaker endpoint status
echo -e "${YELLOW}Checking SageMaker endpoint configuration...${NC}"
SAGEMAKER_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME_PREFIX}-lambda" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='CurrentSageMakerEndpoint'].OutputValue" \
  --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$SAGEMAKER_ENDPOINT" = "NOT_FOUND" ] || [ "$SAGEMAKER_ENDPOINT" = "NOT_CONFIGURED" ]; then
  echo -e "${YELLOW}⚠️  WARNING: SageMaker endpoint is not configured!${NC}"
  echo -e "To make the app fully functional, you need to:"
  echo -e "1. Deploy a SageMaker endpoint using the notebook"
  echo -e "2. Update the Lambda stack with the endpoint name"
  echo -e "   Example: aws cloudformation update-stack --stack-name tech-translator-lambda --use-previous-template --parameters ParameterKey=SageMakerEndpointName,ParameterValue=YOUR_ENDPOINT_NAME --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM"
else
  echo -e "${GREEN}✅ SageMaker endpoint configured: $SAGEMAKER_ENDPOINT${NC}"
fi