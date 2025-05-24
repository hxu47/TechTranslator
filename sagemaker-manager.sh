#!/bin/bash
# sagemaker-manager.sh - Easy SageMaker endpoint management for development

set -e

# Configuration
PROJECT_NAME="TechTranslator"
REGION="us-east-1"
STATE_FILE="sagemaker-state.json"
LAMBDA_STACK_NAME="tech-translator-lambda"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Fixed model configuration
MODEL_ID="google/flan-t5-large"
INSTANCE_TYPE="ml.m5.xlarge"

show_usage() {
    echo -e "${BLUE}TechTranslator SageMaker Manager${NC}"
    echo "=================================="
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo -e "  ${GREEN}deploy${NC}              Deploy SageMaker endpoint (flan-t5-large)"
    echo -e "  ${RED}stop${NC}               Stop current endpoint (saves money!)"
    echo -e "  ${YELLOW}status${NC}             Show current endpoint status"
    echo -e "  ${BLUE}quick-start${NC}        Deploy endpoint AND update Lambda"
    echo -e "  ${BLUE}meeting-prep${NC}       Quick deploy for your one-on-one meeting"
    echo -e "  ${YELLOW}cost${NC}               Show cost information"
    echo -e "  ${RED}cleanup-all${NC}        Remove all SageMaker resources"
    echo ""
    echo "Fixed Configuration:"
    echo "  Model: google/flan-t5-large"
    echo "  Instance: ml.m5.xlarge"
    echo "  Cost: ~\${COST_PER_HOUR}/hour"
    echo ""
    echo "Examples:"
    echo "  $0 deploy              # Deploy flan-t5-large"
    echo "  $0 quick-start         # Deploy + update Lambda"
    echo "  $0 meeting-prep        # Quick setup for demo"
    echo "  $0 stop                # Stop endpoint, save money"
}

load_state() {
    if [ -f "$STATE_FILE" ]; then
        CURRENT_ENDPOINT=$(jq -r '.endpoint_name // empty' "$STATE_FILE" 2>/dev/null || echo "")
        CURRENT_CONFIG=$(jq -r '.endpoint_config_name // empty' "$STATE_FILE" 2>/dev/null || echo "")
        CURRENT_MODEL=$(jq -r '.model_name // empty' "$STATE_FILE" 2>/dev/null || echo "")
        DEPLOY_TIME=$(jq -r '.deploy_time // empty' "$STATE_FILE" 2>/dev/null || echo "")
    else
        CURRENT_ENDPOINT=""
        CURRENT_CONFIG=""
        CURRENT_MODEL=""
        DEPLOY_TIME=""
    fi
}

save_state() {
    local endpoint=$1
    local config=$2
    local model=$3
    
    cat > "$STATE_FILE" << EOF
{
    "endpoint_name": "$endpoint",
    "endpoint_config_name": "$config",
    "model_name": "$model",
    "model_id": "$MODEL_ID",
    "instance_type": "$INSTANCE_TYPE",
    "deploy_time": "$(date -u +%s)",
    "region": "$REGION"
}
EOF
}

clear_state() {
    rm -f "$STATE_FILE"
}

check_endpoint_status() {
    local endpoint_name=$1
    if [ -z "$endpoint_name" ]; then
        echo "NotFound"
        return
    fi
    
    local status=$(aws sagemaker describe-endpoint \
        --endpoint-name "$endpoint_name" \
        --region "$REGION" \
        --query 'EndpointStatus' \
        --output text 2>/dev/null || echo "NotFound")
    
    echo "$status"
}

deploy_endpoint() {
    echo -e "${YELLOW}🚀 Deploying SageMaker endpoint...${NC}"
    echo "Model: $MODEL_ID"
    echo "Instance: $INSTANCE_TYPE"
    echo "Cost: ~\${COST_PER_HOUR}/hour"
    echo ""
    
    # Generate unique names
    local timestamp=$(date +%s)
    local model_name="tech-translator-model-$timestamp"
    local config_name="tech-translator-config-$timestamp"
    local endpoint_name="tech-translator-endpoint-$timestamp"
    
    # Create model
    echo -e "${YELLOW}📦 Creating model...${NC}"
    aws sagemaker create-model \
        --model-name "$model_name" \
        --execution-role-arn "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/LabRole" \
        --primary-container '{
            "Image": "763104351884.dkr.ecr.'$REGION'.amazonaws.com/huggingface-pytorch-inference:2.1.0-transformers4.37.0-gpu-py310-cu121-ubuntu20.04",
            "Environment": {
                "HF_MODEL_ID": "'$MODEL_ID'",
                "HF_TASK": "text2text-generation",
                "SAGEMAKER_CONTAINER_LOG_LEVEL": "20",
                "SAGEMAKER_REGION": "'$REGION'"
            }
        }' \
        --region "$REGION" \
        --tags Key=Project,Value="$PROJECT_NAME" Key=ManagedBy,Value="sagemaker-manager" >/dev/null
    
    # Create endpoint config
    echo -e "${YELLOW}⚙️  Creating endpoint configuration...${NC}"
    aws sagemaker create-endpoint-config \
        --endpoint-config-name "$config_name" \
        --production-variants '[{
            "VariantName": "primary",
            "ModelName": "'$model_name'",
            "InitialInstanceCount": 1,
            "InstanceType": "'$INSTANCE_TYPE'",
            "InitialVariantWeight": 1
        }]' \
        --region "$REGION" \
        --tags Key=Project,Value="$PROJECT_NAME" Key=ManagedBy,Value="sagemaker-manager" >/dev/null
    
    # Create endpoint
    echo -e "${YELLOW}🎯 Creating endpoint...${NC}"
    aws sagemaker create-endpoint \
        --endpoint-name "$endpoint_name" \
        --endpoint-config-name "$config_name" \
        --region "$REGION" \
        --tags Key=Project,Value="$PROJECT_NAME" Key=ManagedBy,Value="sagemaker-manager" >/dev/null
    
    # Save state immediately
    save_state "$endpoint_name" "$config_name" "$model_name"
    
    echo -e "${GREEN}✅ Endpoint creation initiated!${NC}"
    echo -e "${YELLOW}⏳ Waiting for endpoint to be ready...${NC}"
    echo "This usually takes 8-12 minutes for flan-t5-large. You can check status with: $0 status"
    
    # Wait for endpoint
    aws sagemaker wait endpoint-in-service \
        --endpoint-name "$endpoint_name" \
        --region "$REGION"
    
    echo -e "${GREEN}🎉 Endpoint is ready!${NC}"
    echo -e "${GREEN}📍 Endpoint name: $endpoint_name${NC}"
    echo -e "${YELLOW}💰 Now costing ~\${COST_PER_HOUR}/hour${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Update Lambda: $0 update-lambda"
    echo "2. Test integration: $0 test"
    echo "3. When done: $0 stop"
}

stop_endpoint() {
    load_state
    
    if [ -z "$CURRENT_ENDPOINT" ]; then
        echo -e "${YELLOW}ℹ️  No endpoint found to stop${NC}"
        return
    fi
    
    local status=$(check_endpoint_status "$CURRENT_ENDPOINT")
    
    if [ "$status" = "NotFound" ]; then
        echo -e "${YELLOW}ℹ️  Endpoint already deleted${NC}"
        clear_state
        return
    fi
    
    echo -e "${YELLOW}🛑 Stopping SageMaker endpoint: $CURRENT_ENDPOINT${NC}"
    
    # Delete endpoint
    aws sagemaker delete-endpoint \
        --endpoint-name "$CURRENT_ENDPOINT" \
        --region "$REGION" 2>/dev/null || true
    
    # Wait a bit then delete config and model
    echo -e "${YELLOW}⏳ Waiting for endpoint deletion...${NC}"
    sleep 30
    
    aws sagemaker delete-endpoint-config \
        --endpoint-config-name "$CURRENT_CONFIG" \
        --region "$REGION" 2>/dev/null || true
    
    aws sagemaker delete-model \
        --model-name "$CURRENT_MODEL" \
        --region "$REGION" 2>/dev/null || true
    
    clear_state
    echo -e "${GREEN}✅ Endpoint stopped!${NC}"
}

show_status() {
    load_state
    
    echo -e "${BLUE}📊 SageMaker Status${NC}"
    echo "==================="
    
    if [ -z "$CURRENT_ENDPOINT" ]; then
        echo -e "${YELLOW}No endpoint deployed${NC}"
        echo ""
        echo -e "${GREEN}💰 Current cost: \$0/hour${NC}"
        return
    fi
    
    local status=$(check_endpoint_status "$CURRENT_ENDPOINT")
    local status_color
    
    case "$status" in
        "InService") status_color="${GREEN}" ;;
        "Creating"|"Updating") status_color="${YELLOW}" ;;
        "Failed"|"OutOfService") status_color="${RED}" ;;
        "NotFound") status_color="${RED}" ;;
        *) status_color="${NC}" ;;
    esac
    
    echo "Endpoint: $CURRENT_ENDPOINT"
    echo -e "Status: ${status_color}$status${NC}"
    
    if [ -n "$DEPLOY_TIME" ]; then
        local current_time=$(date -u +%s)
        local running_seconds=$((current_time - DEPLOY_TIME))
        local running_hours=$(echo "scale=2; $running_seconds / 3600" | bc -l 2>/dev/null || echo "unknown")
        echo "Running time: ~${running_hours} hours"
        
        echo -e "${YELLOW}💰 Current cost: ~\${COST_PER_HOUR}/hour${NC}"
    fi
    
    if [ "$status" = "NotFound" ]; then
        echo -e "${YELLOW}⚠️  Endpoint not found, clearing state...${NC}"
        clear_state
    fi
}

update_lambda() {
    load_state
    
    if [ -z "$CURRENT_ENDPOINT" ]; then
        echo -e "${RED}❌ No endpoint deployed. Deploy first with: $0 deploy${NC}"
        exit 1
    fi
    
    local status=$(check_endpoint_status "$CURRENT_ENDPOINT")
    if [ "$status" != "InService" ]; then
        echo -e "${RED}❌ Endpoint not ready (status: $status)${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}🔄 Updating Lambda with endpoint: $CURRENT_ENDPOINT${NC}"
    
    aws cloudformation deploy \
        --template-file infrastructure/lambda.yaml \
        --stack-name "$LAMBDA_STACK_NAME" \
        --parameter-overrides SageMakerEndpointName="$CURRENT_ENDPOINT" \
        --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
        --region "$REGION"
    
    echo -e "${GREEN}✅ Lambda updated successfully!${NC}"
}

quick_start() {
    echo -e "${BLUE}🚀 Quick Start: Deploy + Update Lambda${NC}"
    deploy_endpoint
    echo ""
    update_lambda
    echo ""
    echo -e "${GREEN}🎉 Ready to use! Your TechTranslator is fully deployed.${NC}"
}

meeting_prep() {
    echo -e "${BLUE}👔 Meeting Preparation Mode${NC}"
    echo "=========================="
    echo "This will deploy the flan-t5-large model (best quality)"
    echo "Perfect for your one-on-one meeting!"
    echo ""
    quick_start
    echo ""
    echo -e "${YELLOW}🎯 Meeting Checklist:${NC}"
    echo "✅ SageMaker endpoint deployed"
    echo "✅ Lambda function updated"
    echo "• Test your API Gateway endpoint"
    echo "• Prepare demo scenarios"
    echo "• Remember to run '$0 stop' after the meeting!"
}

show_cost_info() {
    echo -e "${BLUE}💰 Cost Information${NC}"
    echo "==================="
    echo ""
    echo "Fixed SageMaker Configuration:"
    echo "  Model: $MODEL_ID"
    echo "  Instance: $INSTANCE_TYPE"
    echo "  Cost: \${COST_PER_HOUR}/hour (\$(echo "scale=2; $COST_PER_HOUR * 24" | bc -l)/day)"
    echo ""
    echo "Other Resources (almost free when idle):"
    echo "  Lambda:   ~\$0.000001 per request"
    echo "  DynamoDB: ~\$0.25/million requests" 
    echo "  S3:       ~\$0.023/GB/month"
    echo "  API GW:   ~\$3.50/million requests"
    echo ""
    echo -e "${GREEN}💡 Tip: Only SageMaker endpoints cost money when idle!${NC}"
    echo ""
    echo "Daily cost examples:"
    echo "  2 hours development: ~\$(echo "scale=2; $COST_PER_HOUR * 2" | bc -l)"
    echo "  8 hours full day: ~\$(echo "scale=2; $COST_PER_HOUR * 8" | bc -l)"
    echo "  Left running 24h: ~\$(echo "scale=2; $COST_PER_HOUR * 24" | bc -l)"
    echo "  1 hour meeting: ~\${COST_PER_HOUR}"
}

test_endpoint() {
    load_state
    
    if [ -z "$CURRENT_ENDPOINT" ]; then
        echo -e "${RED}❌ No endpoint deployed${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}🧪 Testing endpoint: $CURRENT_ENDPOINT${NC}"
    
    aws sagemaker-runtime invoke-endpoint \
        --endpoint-name "$CURRENT_ENDPOINT" \
        --content-type 'application/json' \
        --body '{"inputs": "Explain R-squared to an insurance underwriter."}' \
        --region "$REGION" \
        test-output.json
    
    if [ -f test-output.json ]; then
        echo -e "${GREEN}✅ Test successful!${NC}"
        echo "Response:"
        cat test-output.json | jq -r '.[0].generated_text // . ' 2>/dev/null || cat test-output.json
        rm test-output.json
    else
        echo -e "${RED}❌ Test failed${NC}"
    fi
}

# Main command handling
case "${1:-help}" in
    "deploy")
        deploy_endpoint
        ;;
    "stop")
        stop_endpoint
        ;;
    "status")
        show_status
        ;;
    "update-lambda")
        update_lambda
        ;;
    "quick-start")
        quick_start
        ;;
    "meeting-prep")
        meeting_prep
        ;;
    "test")
        test_endpoint
        ;;
    "cleanup-all")
        stop_endpoint
        echo -e "${GREEN}✅ All SageMaker resources cleaned up${NC}"
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $1${NC}"
        echo ""
        show_usage
        exit 1
        ;;
esac