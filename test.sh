#!/bin/bash
# test-s3.sh

set -e  # Exit immediately if a command exits with a non-zero status

# Configuration
PROJECT_NAME="TechTranslator"
REGION="us-east-1"  # Use the region that's available in your AWS Academy Lab
STACK_NAME_PREFIX="tech-translator"

# Deploy S3 resources
aws cloudformation create-stack \
    --stack-name "${STACK_NAME_PREFIX}-s3" \
    --template-body file://infrastructure/s3.yaml \
    --parameters ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME \
    --region "$REGION"

# Wait for the stack to complete
aws cloudformation wait stack-create-complete \
    --stack-name "${STACK_NAME_PREFIX}-s3" \
    --region "$REGION"

echo "S3 stack deployment completed. Check the AWS Console to verify resources."