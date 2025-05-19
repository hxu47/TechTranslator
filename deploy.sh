#!/bin/bash
# deploy.sh - Script to deploy the TechTranslator CloudFormation stacks

set -e  # Exit immediately if a command exits with a non-zero status

# Configuration
PROJECT_NAME="TechTranslator"
REGION="us-east-1"  # Use the region that's available in your AWS Academy Lab
STACK_NAME_PREFIX="tech-translator"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting deployment of $PROJECT_NAME infrastructure...${NC}"

# Function to deploy a CloudFormation stack
deploy_stack() {
    local stack_name="$1"
    local template_file="$2"
    local parameters="$3"
    
    echo -e "${YELLOW}Deploying $stack_name...${NC}"
    
    # Check if stack exists
    if aws cloudformation describe-stacks --stack-name "$stack_name" --region "$REGION" &> /dev/null; then
        # Update existing stack
        echo "Stack $stack_name exists, updating..."
        if aws cloudformation update-stack \
            --stack-name "$stack_name" \
            --template-body "file://$template_file" \
            --parameters "$parameters" \
            --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
            --region "$REGION"; then
            
            echo "Waiting for stack update to complete..."
            aws cloudformation wait stack-update-complete \
                --stack-name "$stack_name" \
                --region "$REGION"
        else
            echo "No updates to be performed or update failed."
        fi
    else
        # Create new stack
        echo "Creating stack $stack_name..."
        aws cloudformation create-stack \
            --stack-name "$stack_name" \
            --template-body "file://$template_file" \
            --parameters "$parameters" \
            --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
            --region "$REGION"
            
        # Wait for stack creation to complete
        echo "Waiting for stack creation to complete..."
        aws cloudformation wait stack-create-complete \
            --stack-name "$stack_name" \
            --region "$REGION"
    fi
    
    echo -e "${GREEN}Stack $stack_name deployed successfully!${NC}"
}

# Deploy S3 resources
deploy_stack "${STACK_NAME_PREFIX}-s3" "infrastructure/s3.yaml" \
    "ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME"

# get the S3 bucket name from the S3 stack
S3_BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME_PREFIX}-s3" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='WebsiteBucketName'].OutputValue" \
  --output text)

# Deploy DynamoDB resources
deploy_stack "${STACK_NAME_PREFIX}-dynamodb" "infrastructure/dynamodb.yaml" \
    "ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME"

# Deploy Cognito resources
deploy_stack "${STACK_NAME_PREFIX}-cognito" "infrastructure/cognito.yaml" \
    "ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME \
    ParameterKey=S3StackName,ParameterValue=${STACK_NAME_PREFIX}-s3 \
    ParameterKey=WebsiteBucketName,ParameterValue=$S3_BUCKET_NAME"

# Deploy CloudFront resources
deploy_stack "${STACK_NAME_PREFIX}-cloudfront" "infrastructure/cloudfront.yaml" \
    "ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME \
    ParameterKey=S3StackName,ParameterValue=${STACK_NAME_PREFIX}-s3 \
    ParameterKey=WebsiteBucketName,ParameterValue=$S3_BUCKET_NAME"

echo -e "${GREEN}All resources for $PROJECT_NAME have been deployed successfully!${NC}"