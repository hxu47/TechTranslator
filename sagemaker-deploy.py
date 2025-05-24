#!/usr/bin/env python3
"""
sagemaker-deploy.py - Deploy FLAN-T5 using Python SDK (like your notebook)
This approach avoids ECR image issues by using the SageMaker SDK
"""

import boto3
import sagemaker
from sagemaker.huggingface import HuggingFaceModel
import json
import time
import sys
import argparse

def get_execution_role():
    """Get the LabRole ARN"""
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    return f"arn:aws:iam::{account_id}:role/LabRole"

def deploy_model(model_id="google/flan-t5-large", instance_type="ml.m5.xlarge"):
    """Deploy HuggingFace model using SageMaker SDK"""
    
    print(f"🚀 Deploying {model_id} on {instance_type}")
    print("=" * 50)
    
    # Initialize SageMaker session
    sagemaker_session = sagemaker.Session()
    role = get_execution_role()
    
    print(f"📋 Using role: {role}")
    print(f"📋 Region: {sagemaker_session.boto_region_name}")
    
    # Create HuggingFace model
    print("📦 Creating HuggingFace model...")
    hub = {
        'HF_MODEL_ID': model_id,
        'HF_TASK': 'text2text-generation'
    }
    
    huggingface_model = HuggingFaceModel(
        transformers_version="4.37.0",
        pytorch_version="2.1.0", 
        py_version="py310",
        env=hub,
        role=role,
        sagemaker_session=sagemaker_session
    )
    
    # Generate unique endpoint name
    timestamp = int(time.time())
    endpoint_name = f"tech-translator-endpoint-{timestamp}"
    
    print(f"🎯 Deploying endpoint: {endpoint_name}")
    print("⏳ This will take 8-12 minutes...")
    
    try:
        # Deploy the model
        predictor = huggingface_model.deploy(
            initial_instance_count=1,
            instance_type=instance_type,
            endpoint_name=endpoint_name,
            container_startup_health_check_timeout=600,
            model_data_download_timeout=600,
            wait=True
        )
        
        print("✅ Deployment successful!")
        print(f"📍 Endpoint name: {endpoint_name}")
        
        # Save deployment info
        deployment_info = {
            "endpoint_name": endpoint_name,
            "model_name": huggingface_model.name if hasattr(huggingface_model, 'name') else f"huggingface-pytorch-inference-{timestamp}",
            "model_id": model_id,
            "instance_type": instance_type,
            "deploy_time": timestamp,
            "region": sagemaker_session.boto_region_name
        }
        
        with open("sagemaker-state.json", "w") as f:
            json.dump(deployment_info, f, indent=2)
        
        print("📄 Deployment info saved to: sagemaker-state.json")
        
        # Test the endpoint
        print("\n🧪 Testing endpoint...")
        test_payload = {
            "inputs": "Explain R-squared to an insurance underwriter."
        }
        
        response = predictor.predict(test_payload)
        print(f"✅ Test successful!")
        print(f"📝 Response: {response}")
        
        return endpoint_name
        
    except Exception as e:
        print(f"❌ Deployment failed: {str(e)}")
        return None

def cleanup_endpoint(endpoint_name=None):
    """Clean up SageMaker endpoint"""
    
    if not endpoint_name:
        # Try to load from state file
        try:
            with open("sagemaker-state.json", "r") as f:
                state = json.load(f)
                endpoint_name = state.get("endpoint_name")
        except FileNotFoundError:
            print("❌ No endpoint found to cleanup")
            return False
    
    if not endpoint_name:
        print("❌ No endpoint name provided")
        return False
    
    print(f"🧹 Cleaning up endpoint: {endpoint_name}")
    
    try:
        sagemaker_client = boto3.client('sagemaker')
        
        # Delete endpoint
        sagemaker_client.delete_endpoint(EndpointName=endpoint_name)
        print("✅ Endpoint deletion initiated")
        
        # Try to delete endpoint config and model
        # (Names follow SageMaker SDK patterns)
        try:
            # List and delete endpoint configs
            configs = sagemaker_client.list_endpoint_configs(
                NameContains=endpoint_name.replace('endpoint', 'config'),
                MaxResults=10
            )
            for config in configs.get('EndpointConfigs', []):
                config_name = config['EndpointConfigName']
                if endpoint_name.split('-')[-1] in config_name:  # Match timestamp
                    sagemaker_client.delete_endpoint_config(EndpointConfigName=config_name)
                    print(f"✅ Deleted config: {config_name}")
            
            # List and delete models
            models = sagemaker_client.list_models(
                NameContains='huggingface-pytorch-inference',
                MaxResults=10
            )
            for model in models.get('Models', []):
                model_name = model['ModelName']
                if endpoint_name.split('-')[-1] in model_name:  # Match timestamp
                    sagemaker_client.delete_model(ModelName=model_name)
                    print(f"✅ Deleted model: {model_name}")
                    
        except Exception as cleanup_err:
            print(f"⚠️  Some cleanup operations failed: {cleanup_err}")
        
        # Remove state file
        try:
            import os
            os.remove("sagemaker-state.json")
            print("✅ State file removed")
        except:
            pass
            
        print("✅ Cleanup completed!")
        return True
        
    except Exception as e:
        print(f"❌ Cleanup failed: {str(e)}")
        return False

def update_lambda_endpoint(endpoint_name=None):
    """Update Lambda function with new SageMaker endpoint"""
    
    if not endpoint_name:
        # Try to load from state file
        try:
            with open("sagemaker-state.json", "r") as f:
                state = json.load(f)
                endpoint_name = state.get("endpoint_name")
        except FileNotFoundError:
            print("❌ No endpoint found to update Lambda")
            return False
    
    if not endpoint_name:
        print("❌ No endpoint name provided")
        return False
    
    print(f"🔄 Updating Lambda with endpoint: {endpoint_name}")
    
    try:
        import subprocess
        
        # Update CloudFormation stack
        cmd = [
            "aws", "cloudformation", "deploy",
            "--template-file", "infrastructure/lambda.yaml",
            "--stack-name", "tech-translator-lambda",
            "--parameter-overrides", f"SageMakerEndpointName={endpoint_name}",
            "--capabilities", "CAPABILITY_IAM", "CAPABILITY_NAMED_IAM",
            "--region", "us-east-1"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Lambda updated successfully!")
            print(f"📍 Lambda now uses endpoint: {endpoint_name}")
            return True
        else:
            print(f"❌ Lambda update failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Lambda update failed: {str(e)}")
        return False
    """Check current endpoint status"""
    try:
        with open("sagemaker-state.json", "r") as f:
            state = json.load(f)
    except FileNotFoundError:
        print("📊 No endpoint deployed")
        return
    
    endpoint_name = state.get("endpoint_name")
    if not endpoint_name:
        print("📊 No endpoint found in state")
        return
    
    print("📊 SageMaker Status")
    print("=" * 20)
    print(f"Endpoint: {endpoint_name}")
    
    try:
        sagemaker_client = boto3.client('sagemaker')
        response = sagemaker_client.describe_endpoint(EndpointName=endpoint_name)
        status = response['EndpointStatus']
        
        status_emoji = {
            'InService': '🟢',
            'Creating': '🟡', 
            'Updating': '🟡',
            'Failed': '🔴',
            'OutOfService': '🔴'
        }
        
        print(f"Status: {status_emoji.get(status, '⚪')} {status}")
        
        if 'CreationTime' in response:
            creation_time = response['CreationTime']
            running_time = time.time() - creation_time.timestamp()
            hours = running_time / 3600
            print(f"Running time: ~{hours:.1f} hours")
            
    except Exception as e:
        print(f"❌ Could not get status: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='SageMaker FLAN-T5 Deployment')
    parser.add_argument('command', choices=['deploy', 'cleanup', 'status', 'update-lambda', 'quick-start'], 
                       help='Command to execute')
    parser.add_argument('--model', default='google/flan-t5-large',
                       help='HuggingFace model ID')
    parser.add_argument('--instance', default='ml.m5.xlarge',
                       help='SageMaker instance type')
    
    args = parser.parse_args()
    
    if args.command == 'deploy':
        deploy_model(args.model, args.instance)
    elif args.command == 'cleanup':
        cleanup_endpoint()
    elif args.command == 'status':
        check_status()
    elif args.command == 'update-lambda':
        update_lambda_endpoint()
    elif args.command == 'quick-start':
        print("🚀 Quick Start: Deploy + Update Lambda")
        print("=" * 40)
        endpoint_name = deploy_model(args.model, args.instance)
        if endpoint_name:
            print("\n🔄 Updating Lambda...")
            if update_lambda_endpoint(endpoint_name):
                print("\n🎉 Quick start completed successfully!")
                print("✅ SageMaker endpoint deployed")
                print("✅ Lambda function updated")
                print("\n💡 Next: Test your API Gateway endpoint")
            else:
                print("\n⚠️  SageMaker deployed but Lambda update failed")
        else:
            print("\n❌ Quick start failed")

if __name__ == "__main__":
    main()