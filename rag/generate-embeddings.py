import json
import boto3
import os
import uuid
from sentence_transformers import SentenceTransformer
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# This script generates embeddings for knowledge base documents and stores them in DynamoDB
# Run this script in your AWS environment after creating the knowledge base

# Configuration
S3_STACK_NAME = "tech-translator-s3"
DYNAMODB_STACK_NAME = "tech-translator-dynamodb"
REGION = "us-east-1"

# Initialize boto3 clients
cloudformation = boto3.client('cloudformation', region_name=REGION)
s3 = boto3.client('s3', region_name=REGION)
dynamodb = boto3.resource('dynamodb', region_name=REGION)

# Get resource names from CloudFormation outputs
def get_resources():
    # Get S3 bucket name
    s3_response = cloudformation.describe_stacks(StackName=S3_STACK_NAME)
    s3_outputs = s3_response['Stacks'][0]['Outputs']
    
    bucket_name = None
    for output in s3_outputs:
        if output['OutputKey'] == 'KnowledgeBaseBucketName':
            bucket_name = output['OutputValue']
    
    if not bucket_name:
        raise Exception(f"Could not find knowledge base bucket in stack {S3_STACK_NAME}")
    
    # Get DynamoDB table name
    dynamodb_response = cloudformation.describe_stacks(StackName=DYNAMODB_STACK_NAME)
    dynamodb_outputs = dynamodb_response['Stacks'][0]['Outputs']
    
    table_name = None
    for output in dynamodb_outputs:
        if output['OutputKey'] == 'VectorStorageTableName':
            table_name = output['OutputValue']
    
    if not table_name:
        raise Exception(f"Could not find vector storage table in stack {DYNAMODB_STACK_NAME}")
    
    return bucket_name, table_name

# Load all concept documents from S3
def load_concepts(bucket_name):
    concepts = []
    
    # List all objects in the concepts folder
    response = s3.list_objects_v2(
        Bucket=bucket_name,
        Prefix='concepts/'
    )
    
    if 'Contents' not in response:
        raise Exception(f"No concept documents found in s3://{bucket_name}/concepts/")
    
    # Load each concept document
    for obj in response['Contents']:
        key = obj['Key']
        if key.endswith('.json'):
            obj_response = s3.get_object(Bucket=bucket_name, Key=key)
            concept = json.loads(obj_response['Body'].read().decode('utf-8'))
            concepts.append(concept)
            logger.info(f"Loaded concept: {concept['title']}")
    
    return concepts

# Generate chunks for each concept
def generate_chunks(concept):
    chunks = []
    concept_id = concept["concept_id"]
    title = concept["title"]
    
    # Basic definition chunk
    definition = concept["content"]["definition"]
    chunks.append({
        "concept_id": concept_id,
        "vector_id": f"{concept_id}-definition",
        "title": title,
        "text": definition,
        "type": "definition"
    })
    
    # Technical details chunk
    technical_details = concept["content"]["technical_details"]
    chunks.append({
        "concept_id": concept_id,
        "vector_id": f"{concept_id}-technical",
        "title": title,
        "text": technical_details,
        "type": "technical"
    })
    
    # Insurance context chunk
    insurance_context = concept["content"]["insurance_context"]
    chunks.append({
        "concept_id": concept_id,
        "vector_id": f"{concept_id}-context",
        "title": title,
        "text": insurance_context,
        "type": "context"
    })
    
    # Audience-specific explanations
    for audience, explanation in concept["audience_explanations"].items():
        chunks.append({
            "concept_id": concept_id,
            "vector_id": f"{concept_id}-{audience}",
            "title": title,
            "text": explanation,
            "type": "audience",
            "audience": audience
        })
    
    # Examples
    for i, example in enumerate(concept["examples"]):
        chunks.append({
            "concept_id": concept_id,
            "vector_id": f"{concept_id}-example-{i}",
            "title": title,
            "text": example["explanation"],
            "type": "example",
            "context": example["context"]
        })
    
    return chunks

# Generate embeddings for chunks using Sentence Transformers
def generate_embeddings(chunks):
    logger.info("Loading sentence transformer model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')  # Small model suitable for Lambda environments
    
    # Generate embeddings for each chunk
    for chunk in chunks:
        text = chunk["text"]
        logger.info(f"Generating embedding for {chunk['vector_id']}...")
        
        # Generate embedding
        embedding = model.encode(text)
        
        # Store embedding in chunk
        chunk["embedding"] = embedding.tolist()
    
    return chunks

# Store embeddings in DynamoDB
def store_embeddings(chunks, table_name):
    table = dynamodb.Table(table_name)
    
    for chunk in chunks:
        # Prepare item for DynamoDB
        item = {
            "concept_id": chunk["concept_id"],
            "vector_id": chunk["vector_id"],
            "title": chunk["title"],
            "text": chunk["text"],
            "type": chunk["type"],
            "embedding": json.dumps(chunk["embedding"])  # Store as JSON string to avoid DynamoDB list limitations
        }
        
        # Add optional attributes
        if "audience" in chunk:
            item["audience"] = chunk["audience"]
        if "context" in chunk:
            item["context"] = chunk["context"]
        
        # Store in DynamoDB
        table.put_item(Item=item)
        logger.info(f"Stored embedding for {chunk['vector_id']} in DynamoDB")

def main():
    logger.info("Starting embedding generation process...")
    
    # Get resource names
    bucket_name, table_name = get_resources()
    logger.info(f"Using bucket: {bucket_name} and table: {table_name}")
    
    # Load concepts
    concepts = load_concepts(bucket_name)
    logger.info(f"Loaded {len(concepts)} concepts")
    
    # Generate chunks
    all_chunks = []
    for concept in concepts:
        chunks = generate_chunks(concept)
        all_chunks.extend(chunks)
    logger.info(f"Generated {len(all_chunks)} chunks")
    
    # Generate embeddings
    embedded_chunks = generate_embeddings(all_chunks)
    
    # Store embeddings in DynamoDB
    store_embeddings(embedded_chunks, table_name)
    
    logger.info("Embedding generation completed!")

if __name__ == "__main__":
    main()