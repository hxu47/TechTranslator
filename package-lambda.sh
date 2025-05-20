#!/bin/bash
# package-lambda.sh - Script to package Lambda functions

set -e  # Exit immediately if a command fails

# Disable AWS CLI pager to prevent interactive less
export AWS_PAGER=""

# Configuration
LAMBDA_CODE_BUCKET="tech-translator-lambda-code"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Creating Lambda code bucket...${NC}"
# Create the bucket if it doesn't exist
aws s3api create-bucket --bucket $LAMBDA_CODE_BUCKET --region us-east-1 || true

# Function to package a Python Lambda function
package_lambda() {
  func_name=$1
  handler_file=$2
  echo -e "${YELLOW}Packaging $func_name Lambda function...${NC}"
  
  # Save the current directory
  START_DIR=$(pwd)
  
  # Create a temporary directory
  mkdir -p /tmp/lambda-package
  
  # Copy Lambda files to the temporary directory
  cp lambda/$func_name/$handler_file /tmp/lambda-package/lambda_function.py
  cp lambda/$func_name/requirements.txt /tmp/lambda-package/
  
  # Install dependencies
  cd /tmp/lambda-package
  pip install -r requirements.txt -t .
  
  # Zip the package
  zip -r /tmp/$func_name.zip .
  
  # Return to the starting directory
  cd $START_DIR
  
  # Upload to S3
  aws s3 cp /tmp/$func_name.zip s3://$LAMBDA_CODE_BUCKET/$func_name.zip
  
  # Clean up
  rm -rf /tmp/lambda-package
  rm /tmp/$func_name.zip
  
  echo -e "${GREEN}Successfully packaged and uploaded $func_name Lambda function${NC}"
}

# Package Lambda functions
package_lambda "main" "lambda_function.py"
package_lambda "conversation" "lambda_function.py"

echo -e "${GREEN}All Lambda functions packaged and uploaded successfully!${NC}"