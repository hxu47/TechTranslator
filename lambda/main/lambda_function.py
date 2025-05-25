# main lambda - EMAIL-BASED USER ID VERSION
import json
import boto3
import os
import uuid
import re
import hashlib
from datetime import datetime
import logging

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
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-User-Context'
}

def is_valid_email(email):
    """Simple email validation"""
    pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+
    return re.match(pattern, email) is not None

def extract_user_email(event):
    """
    Extract user email from various sources with enhanced fallback logic
    """
    # Method 1: Try Cognito authorizer (if authentication enabled)
    if event.get('requestContext') and event.get('requestContext').get('authorizer'):
        authorizer = event.get('requestContext').get('authorizer')
        if 'claims' in authorizer:
            email = authorizer.get('claims', {}).get('email')
            if email and is_valid_email(email):
                logger.info(f"User email from Cognito: {email}")
                return email.lower().strip()
    
    # Method 2: Try custom headers
    headers = event.get('headers', {})
    user_context = headers.get('X-User-Context') or headers.get('x-user-context')
    
    if user_context and is_valid_email(user_context):
        logger.info(f"User email from header: {user_context}")
        return user_context.lower().strip()
    
    # Method 3: Try request body
    try:
        body = json.loads(event.get('body', '{}')) if event.get('body') else {}
        body_user_context = body.get('user_context')
        if body_user_context and is_valid_email(body_user_context):
            logger.info(f"User email from body: {body_user_context}")
            return body_user_context.lower().strip()
    except:
        pass
    
    # Method 4: Generate session-based email from IP and User-Agent
    source_ip = event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown')
    user_agent = headers.get('User-Agent', headers.get('user-agent', 'unknown'))
    
    if source_ip != 'unknown':
        # Create a stable session ID for anonymous users
        session_string = f"{source_ip}_{user_agent}"
        session_hash = hashlib.md5(session_string.encode()).hexdigest()[:12]
        session_email = f"session_{session_hash}@anonymous.local"
        logger.info(f"Generated session-based email: {session_email}")
        return session_email
    
    # Final fallback
    fallback_email = 'anonymous@anonymous.local'
    logger.info(f"Using fallback email: {fallback_email}")
    return fallback_email

def extract_user_info(user_email):
    """Extract useful information from user email"""
    if '@anonymous.local' in user_email:
        return {
            'email': user_email,
            'domain': 'anonymous',
            'is_company': False,
            'display_name': 'Anonymous User',
            'user_type': 'anonymous'
        }
    
    parts = user_email.split('@')
    if len(parts) != 2:
        return {
            'email': user_email, 
            'domain': 'unknown', 
            'is_company': False,
            'display_name': 'Unknown User',
            'user_type': 'unknown'
        }
    
    local_part, domain = parts
    
    # Extract display name from local part
    display_name = local_part.replace('.', ' ').replace('_', ' ').title()
    
    # Determine if it's a company email
    personal_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com']
    is_company = domain.lower() not in personal_domains
    
    return {
        'email': user_email,
        'domain': domain,
        'is_company': is_company,
        'display_name': display_name,
        'user_type': 'company' if is_company else 'personal'
    }

def lambda_handler(event, context):
    """Main Lambda function with email-based user identification"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Parse request body
        body = json.loads(event.get('body', '{}')) if event.get('body') else {}
        query = body.get('query', '')
        conversation_id = body.get('conversation_id')
        
        # Extract user email with enhanced logic
        user_email = extract_user_email(event)
        user_info = extract_user_info(user_email)
        
        logger.info(f"Processing query for user: {user_email} ({user_info['display_name']}) - Type: {user_info['user_type']}")
        
        if not query:
            return {
                'statusCode': 400,
                'headers': CORS_HEADERS,
                'body': json.dumps({'error': 'Query is required'})
            }
        
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
        conversation_context = get_conversation_context(user_email, conversation_id) if conversation_id else None
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
                    'conversation_id': conversation_id or str(uuid.uuid4()),
                    'user_info': user_info
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
        
        # Store conversation with email as user_id
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        store_conversation(user_email, conversation_id, query, response, concept, audience)
        logger.info(f"Stored conversation: {conversation_id} for user: {user_email}")
        
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'query': query,
                'response': response,
                'concept': concept,
                'audience': audience,
                'conversation_id': conversation_id,
                'user_info': {
                    'email': user_email,
                    'display_name': user_info['display_name'],
                    'domain': user_info['domain'],
                    'user_type': user_info['user_type']
                }
            })
        }
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }

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

def generate_response_with_enhanced_prompts(query, concept_and_audience, relevant_chunks, 
                                          is_follow_up=False, follow_up_type=None, conversation_context=None):
    """Enhanced response generation with FLAN-T5 optimized prompts"""
    try:
        concept = concept_and_audience['concept']
        audience = concept_and_audience['audience']
        concept_display = concept.replace('-', ' ').title()
        
        # Build context from relevant chunks (optimized for FLAN-T5)
        context_text = ""
        if relevant_chunks:
            # Prioritize audience-specific content
            for chunk in relevant_chunks[:2]:  # Only top 2 for FLAN-T5
                item_text = chunk['item']['text']
                # Truncate long text to keep context manageable
                if len(item_text) > 200:
                    item_text = item_text[:200] + "..."
                context_text += f"{item_text}\n\n"
        
        # Generate role-specific, instruction-based prompts for FLAN-T5
        if is_follow_up and follow_up_type:
            prompt = create_follow_up_prompt(query, concept_display, audience, follow_up_type, 
                                           context_text, conversation_context)
        else:
            prompt = create_initial_prompt(query, concept_display, audience, context_text)
        
        # FLAN-T5 optimized parameters
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 200,  # Reasonable length for professional responses
                "temperature": 0.4,     # Lower for more focused responses
                "do_sample": True,
                "top_p": 0.9,
                "repetition_penalty": 1.15,
            }
        }
        
        logger.info(f"Calling FLAN-T5 with prompt type: {'follow_up_' + follow_up_type if is_follow_up else 'initial'}")
        
        # Call SageMaker endpoint
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=SAGEMAKER_ENDPOINT,
            ContentType='application/json',
            Body=json.dumps(payload)
        )
        
        result = json.loads(response['Body'].read().decode())
        
        # Handle FLAN-T5 response format
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
        generated_text = generated_text.strip()
        
        # Enhanced fallback with better responses
        if not generated_text or len(generated_text) < 30:
            logger.warning("FLAN-T5 response too short, using enhanced fallback")
            return create_structured_fallback_response(query, concept_and_audience, relevant_chunks, 
                                                     is_follow_up, follow_up_type)
        
        return generated_text
        
    except Exception as e:
        logger.error(f"Enhanced prompt generation error: {str(e)}")
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

def create_structured_fallback_response(query, concept_and_audience, relevant_chunks, 
                                      is_follow_up=False, follow_up_type=None):
    """Create structured fallback responses when FLAN-T5 fails"""
    concept = concept_and_audience['concept'].replace('-', ' ').title()
    audience = concept_and_audience['audience']
    
    if not relevant_chunks:
        return f"I'd be happy to explain {concept} for insurance {audience}s. Could you ask about a specific aspect you'd like to understand?"
    
    # Get the best matching chunk
    best_chunk = relevant_chunks[0]['item']
    
    # Create structured response based on follow-up type
    if is_follow_up and follow_up_type:
        if follow_up_type == 'example':
            return create_example_response(concept, audience, best_chunk)
        elif follow_up_type == 'scenario':
            return create_scenario_response(concept, audience, best_chunk, query)
        else:
            return f"**{concept} for {audience.title()}s**\n\n{best_chunk['text'][:300]}..."
    else:
        # Initial explanation
        response = f"**{concept} for Insurance {audience.title()}s**\n\n"
        response += best_chunk.get('text', 'Information not available')[:400]
        
        # Add call to action
        if audience == 'underwriter':
            response += "\n\nFor underwriters, this directly impacts your risk assessment and pricing decisions."
        elif audience == 'actuary':
            response += "\n\nAs an actuary, consider this in your model validation and regulatory reporting."
        elif audience == 'executive':
            response += "\n\nThis metric affects your competitive positioning and profitability."
        
        return response

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
def get_conversation_context(user_email, conversation_id):
    """Get the last concept/audience from conversation history"""
    if not conversation_id:
        return None
    
    try:
        payload = {
            'action': 'get',
            'user_id': user_email,  # Using email as user_id
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

def store_conversation(user_email, conversation_id, query, response, concept, audience):
    """Store conversation in DynamoDB via the Conversation Lambda"""
    try:
        payload = {
            'action': 'store',
            'user_id': user_email,  # Using email as user_id
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
        return