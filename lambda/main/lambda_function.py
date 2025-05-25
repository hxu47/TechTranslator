# main lambda - FIXED USER EXTRACTION VERSION
import json
import boto3
import os
import uuid
from datetime import datetime
import logging
import re
import hashlib

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients  
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')
sagemaker_runtime = boto3.client('sagemaker-runtime')

# Get environment variables
VECTOR_TABLE = os.environ.get('VECTOR_TABLE')
KNOWLEDGE_BUCKET = os.environ.get('KNOWLEDGE_BUCKET')
CONVERSATION_FUNCTION = os.environ.get('CONVERSATION_FUNCTION')
SAGEMAKER_ENDPOINT = os.environ.get('SAGEMAKER_ENDPOINT')

# CORS headers for API Gateway integration
CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
}

def lambda_handler(event, context):
    """Main Lambda function - FIXED user extraction"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Parse request body
        body = json.loads(event.get('body', '{}')) if event.get('body') else {}
        query = body.get('query', '')
        conversation_id = body.get('conversation_id')

        # FIXED: Simplified user extraction from Cognito JWT
        user_id = extract_user_email_from_cognito(event)
        logger.info(f"🎯 Extracted user_id: {user_id}")

        if not query:
            return {
                'statusCode': 400,
                'headers': CORS_HEADERS,
                'body': json.dumps({'error': 'Query is required'})
            }
        
        logger.info(f"Processing query: {query} for user: {user_id}")
        
        # Check if SageMaker endpoint is configured
        if not SAGEMAKER_ENDPOINT or SAGEMAKER_ENDPOINT in ['', 'NOT_CONFIGURED', 'PLACEHOLDER']:
            logger.error("SageMaker endpoint not configured")
            return {
                'statusCode': 503,
                'headers': CORS_HEADERS,
                'body': json.dumps({
                    'error': 'AI service temporarily unavailable',
                    'message': 'SageMaker endpoint not configured. Please deploy the model first.',
                    'concept': 'unknown',
                    'audience': 'general'
                })
            }
        
        # Get conversation history to check for context
        conversation_context = get_conversation_context(user_id, conversation_id) if conversation_id else None
        logger.info(f"Conversation context: {conversation_context}")
        
        # Enhanced follow-up detection
        is_follow_up, follow_up_type = detect_follow_up_question(query, conversation_context)
        logger.info(f"Follow-up detection: {is_follow_up}, type: {follow_up_type}")
        
        # Extract concept and audience with better logic
        if is_follow_up and conversation_context:
            concept = conversation_context.get('concept', 'unknown')
            audience = conversation_context.get('audience', 'general')
            logger.info(f"Using preserved context - Concept: {concept}, Audience: {audience}")
        else:
            concept_and_audience = extract_concept_and_audience(query)
            concept = concept_and_audience['concept']
            audience = concept_and_audience['audience']
            logger.info(f"Extracted new context - Concept: {concept}, Audience: {audience}")
        
        # Skip processing if concept is unknown
        if concept == 'unknown':
            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': json.dumps({
                    'query': query,
                    'response': "I can help explain data science and machine learning concepts used in insurance, such as R-squared, loss ratio, and predictive models. Could you please ask about one of these specific topics?",
                    'concept': 'unknown',
                    'audience': audience,
                    'conversation_id': conversation_id or str(uuid.uuid4())
                })
            }
        
        # Get relevant context from DynamoDB with better filtering
        relevant_chunks = get_relevant_context_enhanced(concept, audience, query)
        logger.info(f"Retrieved {len(relevant_chunks)} relevant chunks")
        
        # Generate response using enhanced FLAN-T5 prompting
        response = generate_response_with_enhanced_prompts(
            query, 
            {'concept': concept, 'audience': audience}, 
            relevant_chunks, 
            is_follow_up,
            follow_up_type,
            conversation_context
        )
        logger.info("Generated response using enhanced prompts")
        
        # Store conversation
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        store_conversation(user_id, conversation_id, query, response, concept, audience)
        logger.info(f"Stored conversation: {conversation_id}")
        
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'query': query,
                'response': response,
                'concept': concept,
                'audience': audience,
                'conversation_id': conversation_id
            })
        }
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }

def extract_user_email_from_cognito(event):
    """
    DEBUG VERSION: Enhanced logging to identify the exact issue
    """
    try:
        # Log the ENTIRE event structure for debugging
        logger.info("🚨 DEBUG: Full event structure:")
        logger.info(json.dumps(event, indent=2, default=str))
        
        # Method 1: Try to get from authorizer context
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        
        logger.info(f"🔍 DEBUG: Request context keys: {list(request_context.keys())}")
        logger.info(f"🔍 DEBUG: Authorizer structure: {json.dumps(authorizer, indent=2, default=str)}")
        
        # Check if authorizer is empty (means no authentication)
        if not authorizer:
            logger.warning("⚠️ DEBUG: No authorizer found - API might not be using authentication!")
            
            # Check if there's identity info (unauthenticated requests)
            identity = request_context.get('identity', {})
            logger.info(f"🔍 DEBUG: Identity info: {json.dumps(identity, indent=2, default=str)}")
            
            source_ip = identity.get('sourceIp', 'unknown')
            if source_ip != 'unknown':
                session_hash = hashlib.md5(source_ip.encode()).hexdigest()[:12]
                fallback_email = f"guest_{session_hash}@anonymous.local"
                logger.warning(f"⚠️ DEBUG: Creating guest user from IP: {fallback_email}")
                return fallback_email
            
            return 'no_auth@anonymous.local'
        
        # Check for claims in authorizer
        claims = authorizer.get('claims', {})
        if claims:
            logger.info(f"✅ DEBUG: Found claims: {json.dumps(claims, indent=2, default=str)}")
            
            # Try email first
            email = claims.get('email')
            if email and re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
                logger.info(f"✅ DEBUG: Found valid email in claims: {email}")
                return email.lower().strip()
            
            # Try cognito:username as backup
            username = claims.get('cognito:username')
            if username:
                logger.info(f"✅ DEBUG: Found cognito:username: {username}")
                if '@' in username:
                    return username.lower().strip()
                else:
                    user_email = f"{username}@cognito.local"
                    logger.info(f"✅ DEBUG: Created email from username: {user_email}")
                    return user_email
            
            # Try sub as last resort
            sub = claims.get('sub')
            if sub:
                user_email = f"{sub}@cognito.local"
                logger.info(f"✅ DEBUG: Created email from sub: {user_email}")
                return user_email
            
            logger.warning(f"⚠️ DEBUG: Claims found but no usable identifiers: {list(claims.keys())}")
        else:
            logger.warning("⚠️ DEBUG: No claims found in authorizer")
        
        # Method 2: Direct authorizer fields
        logger.info("🔍 DEBUG: Checking direct authorizer fields...")
        for key, value in authorizer.items():
            logger.info(f"  - {key}: {value}")
        
        email = authorizer.get('email')
        if email and re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            logger.info(f"✅ DEBUG: Found direct email in authorizer: {email}")
            return email.lower().strip()
        
        # Method 3: Check principalId
        principal_id = authorizer.get('principalId')
        if principal_id:
            logger.info(f"✅ DEBUG: Found principalId: {principal_id}")
            if '@' in principal_id:
                return principal_id.lower().strip()
            else:
                user_email = f"{principal_id}@principal.local"
                logger.info(f"✅ DEBUG: Created email from principalId: {user_email}")
                return user_email
        
        # If we get here, authentication might not be working
        logger.error("❌ DEBUG: No user identification found - possible authentication issues!")
        logger.error(f"❌ DEBUG: Full authorizer dump: {json.dumps(authorizer)}")
        
        # Create fallback based on source IP
        identity = request_context.get('identity', {})
        source_ip = identity.get('sourceIp', 'unknown')
        if source_ip != 'unknown':
            session_hash = hashlib.md5(source_ip.encode()).hexdigest()[:12]
            fallback_email = f"guest_{session_hash}@anonymous.local"
            logger.warning(f"⚠️ DEBUG: Final fallback - created guest from IP: {fallback_email}")
            return fallback_email
        
        return 'debug_failed@anonymous.local'
        
    except Exception as e:
        logger.error(f"❌ DEBUG: Error in extract_user_email_from_cognito: {str(e)}")
        logger.error(f"❌ DEBUG: Exception type: {type(e)}")
        import traceback
        logger.error(f"❌ DEBUG: Traceback: {traceback.format_exc()}")
        return 'exception@anonymous.local'
        
# Keep all the other functions exactly the same...
# (extract_concept_and_audience, detect_follow_up_question, etc.)

def extract_concept_and_audience(query):
    """Enhanced concept and audience extraction"""
    query_lower = query.lower()
    
    # Enhanced concept mapping with more keywords
    concept_keywords = {
        'r-squared': [
            'r squared', 'r-squared', 'r2', 'r²', 'coefficient of determination', 
            'r square', 'goodness of fit', 'variance explained', 'model fit'
        ],
        'loss-ratio': [
            'loss ratio', 'claims ratio', 'incurred losses', 'loss ratios',
            'claim ratio', 'losses to premiums', 'loss rate', 'claim rate'
        ],
        'predictive-model': [
            'predictive model', 'prediction model', 'machine learning', 'ml model', 
            'models', 'modeling', 'algorithm', 'statistical model', 'data model',
            'pricing model', 'risk model', 'glm', 'regression'
        ]
    }
    
    detected_concept = None
    # Find the best matching concept (most specific first)
    concept_scores = {}
    for concept_id, keywords in concept_keywords.items():
        score = sum(1 for keyword in keywords if keyword in query_lower)
        if score > 0:
            concept_scores[concept_id] = score
    
    if concept_scores:
        # Pick the concept with highest score
        detected_concept = max(concept_scores, key=concept_scores.get)
    else:
        detected_concept = 'unknown'
    
    # Enhanced audience mapping
    audience_keywords = {
        'underwriter': ['underwriter', 'underwriting', 'underwriters', 'uw'],
        'actuary': ['actuary', 'actuarial', 'actuaries', 'pricing actuary'],
        'executive': ['executive', 'ceo', 'manager', 'leadership', 'executives', 'management', 'director']
    }
    
    detected_audience = None
    for audience_id, keywords in audience_keywords.items():
        if any(keyword in query_lower for keyword in keywords):
            detected_audience = audience_id
            break
    
    if not detected_audience:
        detected_audience = 'general'
    
    return {'concept': detected_concept, 'audience': detected_audience}

def detect_follow_up_question(query, conversation_context):
    """Enhanced follow-up question detection with type classification"""
    if not conversation_context:
        return False, None
    
    query_lower = query.lower().strip()
    
    # Classify different types of follow-ups
    follow_up_types = {
        'example': ['example', 'give me an example', 'show me', 'for instance', 'can you give'],
        'clarification': ['what does it mean', 'what does that mean', 'explain that', 'clarify', 'i don\'t understand'],
        'elaboration': ['tell me more', 'more about', 'elaborate', 'expand on', 'more details'],
        'scenario': ['what if', 'suppose', 'if', 'when', 'in case of'],
        'comparison': ['vs', 'versus', 'compared to', 'difference', 'how does it compare'],
        'application': ['how do i', 'how to', 'steps', 'process', 'implement']
    }
    
    # Check for strong follow-up indicators
    for follow_up_type, patterns in follow_up_types.items():
        if any(pattern in query_lower for pattern in patterns):
            return True, follow_up_type
    
    # Check for short questions (likely follow-ups)
    if len(query.split()) <= 10 and any(word in query_lower for word in ['why', 'how', 'when', 'what', 'where']):
        return True, 'clarification'
    
    # Check if query doesn't contain full concept keywords (indicating follow-up)
    full_concept_keywords = ['what is', 'explain', 'define', 'tell me about']
    has_full_intro = any(keyword in query_lower for keyword in full_concept_keywords)
    
    if not has_full_intro and len(query.split()) <= 15:
        return True, 'elaboration'
    
    return False, None

def get_relevant_context_enhanced(concept, audience, query, max_items=3):
    """Enhanced context retrieval with better filtering"""
    try:
        table = dynamodb.Table(VECTOR_TABLE)
        
        # Query by concept_id
        response = table.query(
            KeyConditionExpression="concept_id = :concept_id",
            ExpressionAttributeValues={":concept_id": concept},
            Limit=10  # Get more initially, then filter
        )
        
        items = response.get('Items', [])
        if not items:
            return []
        
        # Enhanced prioritization logic
        prioritized_items = []
        
        # 1. Exact audience matches get highest priority
        audience_matches = [item for item in items if item.get('audience') == audience]
        prioritized_items.extend(audience_matches[:2])  # Top 2 audience matches
        
        # 2. Add definition if not already included
        if not any(item.get('type') == 'definition' for item in prioritized_items):
            definition_items = [item for item in items if item.get('type') == 'definition']
            if definition_items:
                prioritized_items.append(definition_items[0])
        
        # 3. Add context/examples if space remains
        remaining_slots = max_items - len(prioritized_items)
        if remaining_slots > 0:
            other_items = [item for item in items 
                          if item not in prioritized_items 
                          and item.get('type') in ['context', 'example', 'technical']]
            prioritized_items.extend(other_items[:remaining_slots])
        
        # Convert to expected format
        return [{'item': item, 'similarity': 1.0} for item in prioritized_items[:max_items]]
        
    except Exception as e:
        logger.error(f"Error getting enhanced context: {str(e)}")
        return []

# Include all other functions from your original code...
def create_structured_fallback_response(query, concept_and_audience, relevant_chunks, 
                                      is_follow_up=False, follow_up_type=None):
    """Create clean fallback responses without redundant titles"""
    concept = concept_and_audience['concept'].replace('-', ' ').title()
    audience = concept_and_audience['audience']
    
    if not relevant_chunks:
        return f"I'd be happy to explain {concept} for insurance {audience}s. Could you ask about a specific aspect you'd like to understand?"
    
    # Get the best matching chunk
    best_chunk = relevant_chunks[0]['item']
    
    # Create clean response without redundant titles
    if is_follow_up and follow_up_type:
        if follow_up_type == 'example':
            return create_example_response(concept, audience, best_chunk)
        elif follow_up_type == 'scenario':
            return create_scenario_response(concept, audience, best_chunk, query)
        else:
            # Just return the clean content without extra formatting
            clean_text = clean_chunk_text(best_chunk['text'])
            return clean_text[:400] + ("..." if len(clean_text) > 400 else "")
    else:
        # Initial explanation - CLEAN VERSION (no redundant titles)
        clean_text = clean_chunk_text(best_chunk.get('text', 'Information not available'))
        
        # Just return the content directly - no extra title formatting
        response = clean_text[:400] + ("..." if len(clean_text) > 400 else "")
        
        # Add audience-specific context if the response is too generic
        if len(response) < 100:  # Only add context if response is very short
            if audience == 'underwriter':
                response += " This directly impacts your risk assessment and pricing decisions."
            elif audience == 'actuary':
                response += " Consider this in your model validation and regulatory reporting."
            elif audience == 'executive':
                response += " This affects your competitive positioning and profitability."
        
        return response

def clean_chunk_text(text):
    """Clean up chunk text by removing ALL redundant prefixes and formatting"""
    if not text:
        return ""
    
    # Remove the problematic prefixes that are creating the issue
    prefixes_to_remove = [
        "Action guidance: ",
        "**Loss Ratio for Insurance Executives** ",
        "**Loss Ratio for Insurance Underwriters** ",
        "**Loss Ratio for Insurance Actuaries** ",
        "**R-squared for Insurance Executives** ",
        "**R-squared for Insurance Underwriters** ", 
        "**R-squared for Insurance Actuaries** ",
        "**Predictive Model for Insurance Executives** ",
        "**Predictive Model for Insurance Underwriters** ",
        "**Predictive Model for Insurance Actuaries** ",
    ]
    
    cleaned_text = text
    for prefix in prefixes_to_remove:
        if cleaned_text.startswith(prefix):
            cleaned_text = cleaned_text[len(prefix):].strip()
            break
    
    # Remove any remaining markdown bold formatting
    cleaned_text = cleaned_text.replace("**", "")
    
    # Remove double spaces and clean up
    cleaned_text = " ".join(cleaned_text.split())
    
    return cleaned_text

def generate_response_with_enhanced_prompts(query, concept_and_audience, relevant_chunks, 
                                          is_follow_up=False, follow_up_type=None, conversation_context=None):
    """Enhanced response generation - CLEAN VERSION"""
    try:
        concept = concept_and_audience['concept']
        audience = concept_and_audience['audience']
        concept_display = concept.replace('-', ' ').title()
        
        # Build clean context from relevant chunks
        context_text = ""
        if relevant_chunks:
            for chunk in relevant_chunks[:2]:
                item_text = chunk['item']['text']
                # Clean the text before using it in prompts
                item_text = clean_chunk_text(item_text)
                if len(item_text) > 200:
                    item_text = item_text[:200] + "..."
                context_text += f"{item_text}\n\n"
        
        # Generate prompts
        if is_follow_up and follow_up_type:
            prompt = create_follow_up_prompt(query, concept_display, audience, follow_up_type, 
                                           context_text, conversation_context)
        else:
            prompt = create_initial_prompt(query, concept_display, audience, context_text)
        
        # FLAN-T5 parameters
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 200,
                "temperature": 0.4,
                "do_sample": True,
                "top_p": 0.9,
                "repetition_penalty": 1.15,
            }
        }
        
        # Call SageMaker endpoint
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=SAGEMAKER_ENDPOINT,
            ContentType='application/json',
            Body=json.dumps(payload)
        )
        
        result = json.loads(response['Body'].read().decode())
        
        # Handle response format
        if isinstance(result, list) and len(result) > 0:
            if isinstance(result[0], dict):
                generated_text = result[0].get('generated_text', '')
            else:
                generated_text = str(result[0])
        elif isinstance(result, dict):
            generated_text = result.get('generated_text', '')
        else:
            generated_text = str(result)
        
        # Clean up the response
        generated_text = clean_chunk_text(generated_text.strip())
        
        # Use fallback if response is too short
        if not generated_text or len(generated_text) < 30:
            return create_structured_fallback_response(query, concept_and_audience, relevant_chunks, 
                                                     is_follow_up, follow_up_type)
        
        return generated_text
        
    except Exception as e:
        logger.error(f"Response generation error: {str(e)}")
        return create_structured_fallback_response(query, concept_and_audience, relevant_chunks, 
                                                 is_follow_up, follow_up_type)

def create_initial_prompt(query, concept_display, audience, context_text):
    """Create optimized initial explanation prompts for FLAN-T5"""
    
    # Role-specific prompt templates
    role_prompts = {
        'underwriter': f"""Task: Explain {concept_display} to an insurance underwriter.

Context: {context_text.strip()}

Requirements:
- Focus on risk assessment and pricing decisions
- Include practical examples with numbers
- Explain impact on underwriting process
- Keep response professional and actionable

Question: {query}

Explanation:""",

        'actuary': f"""Task: Explain {concept_display} to an insurance actuary.

Context: {context_text.strip()}

Requirements:
- Focus on statistical accuracy and model validation
- Include technical details and mathematical context
- Explain regulatory and compliance implications
- Provide quantitative examples

Question: {query}

Explanation:""",

        'executive': f"""Task: Explain {concept_display} to an insurance executive.

Context: {context_text.strip()}

Requirements:
- Focus on business impact and strategic implications
- Include ROI and competitive advantage aspects
- Use clear, non-technical language
- Provide actionable insights

Question: {query}

Explanation:""",

        'general': f"""Task: Explain {concept_display} in insurance context.

Context: {context_text.strip()}

Requirements:
- Provide clear definition and practical examples
- Include real-world insurance applications
- Use professional but accessible language
- Focus on practical understanding

Question: {query}

Explanation:"""
    }
    
    return role_prompts.get(audience, role_prompts['general'])

def create_follow_up_prompt(query, concept_display, audience, follow_up_type, context_text, conversation_context):
    """Create optimized follow-up prompts based on question type"""
    
    # Get previous context summary
    prev_summary = f"Previously discussed {concept_display} for {audience}s."
    
    follow_up_prompts = {
        'example': f"""Task: Provide a specific example of {concept_display} for an insurance {audience}.

Context: {context_text.strip()}

Previous discussion: {prev_summary}

Requirements:
- Give a concrete, realistic example with numbers
- Show practical application in insurance
- Make it relevant to {audience} work

Follow-up request: {query}

Example:""",

        'clarification': f"""Task: Clarify {concept_display} concept for an insurance {audience}.

Context: {context_text.strip()}

Previous discussion: {prev_summary}

Requirements:
- Address the specific confusion or question
- Use simpler terms if needed
- Provide additional context

Clarification needed: {query}

Clarification:""",

        'elaboration': f"""Task: Provide more details about {concept_display} for an insurance {audience}.

Context: {context_text.strip()}

Previous discussion: {prev_summary}

Requirements:
- Build on previous explanation
- Add deeper insights or additional aspects
- Maintain focus on {audience} needs

Request for more information: {query}

Additional details:""",

        'scenario': f"""Task: Explain {concept_display} scenario for an insurance {audience}.

Context: {context_text.strip()}

Previous discussion: {prev_summary}

Requirements:
- Address the specific scenario or condition
- Explain what happens in that situation
- Provide practical guidance

Scenario question: {query}

Scenario explanation:""",

        'application': f"""Task: Explain how to apply {concept_display} for an insurance {audience}.

Context: {context_text.strip()}

Previous discussion: {prev_summary}

Requirements:
- Provide step-by-step guidance
- Focus on practical implementation
- Include tips and best practices

Implementation question: {query}

Implementation guidance:"""
    }
    
    return follow_up_prompts.get(follow_up_type, follow_up_prompts['elaboration'])

def create_example_response(concept, audience, chunk):
    """Create example-focused responses"""
    examples = {
        'r-squared': {
            'underwriter': "Example: Your auto insurance pricing model has an R-squared of 0.68. This means 68% of premium differences across policies are explained by your rating factors (age, location, vehicle type). The remaining 32% represents unexplained variation - potentially missed risk factors that competitors might be capturing.",
            'actuary': "Example: In your homeowners GLM, an R-squared of 0.75 indicates strong model performance. Compare this to industry benchmarks (typically 0.60-0.80 for property). Higher R-squared suggests your variable selection and model specification are capturing the key risk drivers effectively.",
            'executive': "Example: Your commercial lines pricing model achieved R-squared of 0.72, compared to 0.65 last year. This 7-point improvement translates to better risk selection, potentially reducing loss ratios by 2-3 percentage points and improving underwriting margins."
        },
        'loss-ratio': {
            'underwriter': "Example: Your personal auto book shows a 78% loss ratio. With a 25% expense ratio, your combined ratio is 103% - meaning you're losing 3 cents on every premium dollar. You need rate increases or tighter underwriting guidelines to achieve profitability.",
            'actuary': "Example: Analyzing loss ratios by coverage: collision at 65%, comprehensive at 45%, liability at 85%. The high liability ratio indicates potential adverse selection or inadequate pricing for this coverage, requiring detailed analysis of claim frequency and severity trends.",
            'executive': "Example: Loss ratio increased from 72% to 78% over six quarters. This 6-point deterioration, if sustained, reduces underwriting profit by $12M annually on a $200M premium book, significantly impacting your competitive position and ROE."
        }
    }
    
    concept_key = concept.lower().replace(' ', '-')
    if concept_key in examples and audience in examples[concept_key]:
        return examples[concept_key][audience]
    else:
        return f"Here's a practical example of {concept} for {audience}s: {chunk['text'][:200]}..."

def create_scenario_response(concept, audience, chunk, query):
    """Create scenario-based responses"""
    query_lower = query.lower()
    
    # Common scenario patterns
    if 'zero' in query_lower or '0' in query_lower:
        if 'r-squared' in concept.lower():
            return f"If R-squared is 0, it means your pricing model explains none of the premium variation - essentially random pricing. For {audience}s, this signals a complete model failure requiring immediate attention to rating factor selection and model rebuild."
        elif 'loss ratio' in concept.lower():
            return f"A loss ratio of 0% would mean no claims paid, which is unrealistic. However, very low loss ratios (under 30%) might indicate over-pricing, potential market share loss, or unusual claim development patterns requiring investigation."
    
    elif 'high' in query_lower:
        if 'r-squared' in concept.lower():
            return f"High R-squared (above 0.8) for {audience}s could indicate excellent model performance OR potential overfitting. Validate with out-of-sample testing and ensure the model performs well on new data before deployment."
        elif 'loss ratio' in concept.lower():
            return f"High loss ratios (above 85%) signal profitability concerns. For {audience}s, this requires immediate action: rate increases, underwriting tightening, or coverage modifications to restore margins."
    
    # Default scenario response
    return f"In that scenario with {concept}: {chunk['text'][:250]}..."

# Keep existing helper functions
def get_conversation_context(user_id, conversation_id):
    """Get the last concept/audience from conversation history"""
    if not conversation_id:
        return None
    
    try:
        payload = {
            'action': 'get',
            'user_id': user_id,
            'conversation_id': conversation_id
        }
        
        response = lambda_client.invoke(
            FunctionName=CONVERSATION_FUNCTION,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') == 200 and result.get('conversations'):
            conversations = result['conversations']
            if conversations:
                for conv in sorted(conversations, key=lambda x: x.get('timestamp', ''), reverse=True):
                    if conv.get('concept') and conv.get('concept') != 'unknown':
                        return {
                            'concept': conv.get('concept'),
                            'audience': conv.get('audience', 'general')
                        }
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting conversation context: {str(e)}")
        return None

def store_conversation(user_id, conversation_id, query, response, concept, audience):
    """Store conversation in DynamoDB via the Conversation Lambda"""
    try:
        payload = {
            'action': 'store',
            'user_id': user_id,
            'conversation_id': conversation_id,
            'query': query,
            'response': response,
            'concept': concept,
            'audience': audience
        }
        
        response = lambda_client.invoke(
            FunctionName=CONVERSATION_FUNCTION,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        return json.loads(response['Payload'].read())
    except Exception as e:
        logger.error(f"Error storing conversation: {str(e)}")
        return None