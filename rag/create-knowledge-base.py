import json
import boto3
import os
import uuid

# This script creates and uploads structured knowledge base documents to S3
# Run this script in your AWS environment after deploying infrastructure

# Configuration
STACK_NAME = "tech-translator-s3"  # Your CloudFormation stack name
REGION = "us-east-1"  # Your AWS region

# Initialize boto3 clients
cloudformation = boto3.client('cloudformation', region_name=REGION)
s3 = boto3.client('s3', region_name=REGION)

# Get S3 bucket name from CloudFormation output
def get_bucket_name():
    response = cloudformation.describe_stacks(StackName=STACK_NAME)
    outputs = response['Stacks'][0]['Outputs']
    for output in outputs:
        if output['OutputKey'] == 'KnowledgeBaseBucketName':
            return output['OutputValue']
    raise Exception(f"Could not find knowledge base bucket in stack {STACK_NAME}")

# Create knowledge base documents
def create_knowledge_base_documents():
    # Insurance data science concepts
    concepts = [
        {
            "concept_id": "r-squared",
            "title": "R-squared",
            "content": {
                "definition": "R-squared (R²) is a statistical measure that represents the proportion of the variance for a dependent variable that's explained by independent variables in a regression model.",
                "technical_details": "R-squared values range from 0 to 1, where 0 indicates that the model explains none of the variability, and 1 indicates perfect prediction. It is calculated as 1 minus the ratio of the residual sum of squares to the total sum of squares.",
                "insurance_context": "In insurance pricing, R-squared helps actuaries understand how well factors like age, location, or claim history explain premium variations. A high R-squared indicates that the selected rating factors are good predictors of risk.",
                "limitations": "R-squared will always increase as more variables are added to a model, even if those variables are not significant. Adjusted R-squared addresses this limitation by penalizing the addition of variables that don't improve the model."
            },
            "audience_explanations": {
                "underwriter": "As an underwriter, you can think of R-squared as a measure of how well your pricing model captures risk factors. If your pricing model has an R-squared of 0.75, it means that 75% of the premium variation is explained by the factors in your model, while 25% remains unexplained. This unexplained portion might represent risk factors you're not capturing, which could lead to adverse selection if competitors have better models.",
                "actuary": "When comparing generalized linear models (GLMs) for pricing, the model with higher R-squared (all else being equal) is explaining more of the variance in loss ratios across segments. However, be cautious of overfitting - a model with too many parameters might have a high R-squared on training data but perform poorly on new data. Cross-validation and consideration of information criteria like AIC and BIC are essential complements to R-squared evaluation.",
                "executive": "R-squared provides a simple measure of how well our predictive models are working. An R-squared of 0.8 means our pricing model captures 80% of what drives premium differences, indicating a strong predictive model. The remaining 20% represents potential opportunity for competitive advantage if we can identify additional predictive factors that our competitors haven't discovered yet."
            },
            "examples": [
                {
                    "context": "Auto Insurance Pricing",
                    "explanation": "In an auto insurance pricing model, an R-squared of 0.72 indicates that factors like driver age, vehicle type, and prior claims explain 72% of the variation in claim costs across policyholders."
                },
                {
                    "context": "Policy Renewal Prediction",
                    "explanation": "A customer retention model with an R-squared of 0.35 suggests that while you have some predictive power, much of what drives customers to renew or leave remains unexplained by your current variables."
                }
            ],
            "related_concepts": ["predictive modeling", "statistical significance", "p-value", "adjusted r-squared"]
        },
        {
            "concept_id": "loss-ratio",
            "title": "Loss Ratio",
            "content": {
                "definition": "Loss ratio is a key insurance metric that measures the relationship between incurred losses and earned premiums, expressed as a percentage.",
                "technical_details": "The basic formula is: Loss Ratio = (Incurred Losses + Loss Adjustment Expenses) / Earned Premiums × 100%. A combined ratio additionally includes underwriting expenses and is calculated as Loss Ratio + Expense Ratio.",
                "insurance_context": "Loss ratio is one of the most important profitability metrics in insurance. Generally, a loss ratio below 100% indicates underwriting profit (before considering investment income), while a ratio above 100% indicates an underwriting loss.",
                "limitations": "Loss ratios can be volatile in the short term, especially for low-frequency, high-severity lines of business or for small portfolios. Loss ratios also don't account for the time value of money or investment income."
            },
            "audience_explanations": {
                "underwriter": "If you're seeing a loss ratio of 85% in a particular segment, it means that for every $100 in premium, $85 is being paid out in claims and claim expenses. This leaves only $15 for operational expenses, commissions, and profit. If your company's expense ratio is 20%, this segment is operating at a 5% loss. You may need to consider rate adjustments or tighter underwriting guidelines for this segment.",
                "actuary": "When modeling loss ratios, we need to consider both frequency and severity trends, as well as large claim volatility and development patterns. A pure loss ratio that excludes IBNR and case reserve development can give a misleading picture of profitability. For long-tail lines, analyzing loss ratios by accident year versus calendar year can reveal important trends in ultimate loss expectations.",
                "executive": "A loss ratio trend that increases from 60% to 70% over three quarters may signal emerging profitability challenges that require attention. With an expense ratio of 25%, this change would reduce your combined ratio from a profitable 85% to a borderline 95%, significantly impacting your underwriting margin. This trend could be due to inflation, changing risk profiles, competitor pricing actions, or claims handling efficiency."
            },
            "examples": [
                {
                    "context": "Property Insurance Performance",
                    "explanation": "A homeowners insurance portfolio with a 65% loss ratio and 30% expense ratio yields a combined ratio of 95%, indicating a 5% underwriting profit margin."
                },
                {
                    "context": "Line of Business Comparison",
                    "explanation": "Commercial auto typically runs at higher loss ratios (around 75-80%) compared to commercial property (around 50-60%), which means pricing, underwriting, and reinsurance strategies need to be tailored differently for these lines."
                }
            ],
            "related_concepts": ["combined ratio", "expense ratio", "underwriting profit", "IBNR", "loss development"]
        },
        {
            "concept_id": "predictive-model",
            "title": "Predictive Model",
            "content": {
                "definition": "A predictive model is a statistical algorithm that uses historical data to predict future outcomes or classify new data points.",
                "technical_details": "Common predictive modeling techniques include linear and logistic regression, decision trees, random forests, gradient boosting machines, neural networks, and ensemble methods. Models are evaluated using metrics like accuracy, precision, recall, F1-score, AUC-ROC, and mean squared error.",
                "insurance_context": "In insurance, predictive models help estimate the likelihood of claims, premium adequacy, customer behavior, and fraud. They are used throughout the insurance lifecycle, from marketing and underwriting to claims management and renewal.",
                "limitations": "Predictive models can only identify patterns present in historical data, may struggle with rare events, and can perpetuate historical biases if not carefully designed. They also require ongoing monitoring and retraining as conditions change."
            },
            "audience_explanations": {
                "underwriter": "The predictive model flags applications with risk scores based on patterns in historical data. For example, if an application scores in the highest risk decile, it has characteristics similar to policies that historically had 2.5 times more claims than average. These models don't replace your judgment - they provide an additional data point to complement your expertise, especially for factors that might not be obvious from traditional underwriting guidelines.",
                "actuary": "When building predictive models for insurance applications, we need to balance predictive power with interpretability and regulatory compliance. A black-box model might achieve higher accuracy but could raise regulatory concerns about explainability. Generalized linear models (GLMs) remain popular in insurance because they provide a good balance of predictive power and interpretability, with clear indications of which factors drive predictions and by how much.",
                "executive": "Our predictive models give us a competitive edge by identifying patterns that traditional approaches might miss. For example, our customer retention predictive model has improved retention by 5% by identifying at-risk policies before renewal, allowing targeted interventions. This translates to approximately $2M in saved premium that would otherwise have been lost, with minimal additional operational cost."
            },
            "examples": [
                {
                    "context": "Claims Triage",
                    "explanation": "A predictive model analyzes new claims and assigns each a complexity score from 1-10. Claims scoring 8+ are automatically routed to senior adjusters, while scores of 3 or below are fast-tracked for simple processing, optimizing adjuster workloads."
                },
                {
                    "context": "Premium Leakage Detection",
                    "explanation": "A random forest model analyzes policy characteristics and identifies applications with a high probability of misclassification or missing information, flagging them for underwriter review before binding to prevent premium leakage."
                }
            ],
            "related_concepts": ["machine learning", "artificial intelligence", "data mining", "feature engineering", "model validation"]
        },
        {
            "concept_id": "credibility-theory",
            "title": "Credibility Theory",
            "content": {
                "definition": "Credibility theory is a statistical technique that combines multiple estimates to create an optimal prediction, typically blending individual experience with broader population data.",
                "technical_details": "The credibility formula is Z × Individual Experience + (1-Z) × Collective Experience, where Z is the credibility factor ranging from 0 to 1. In Bühlmann credibility, Z = n/(n+K), where n is the number of observations and K is the credibility parameter that depends on the variance components.",
                "insurance_context": "In insurance pricing and reserving, credibility theory helps determine how much weight to give to a specific risk's experience versus industry-wide or class data. It's especially valuable for small portfolios or individual risks where experience is limited.",
                "limitations": "Traditional credibility methods assume a stable underlying risk process and may not adapt quickly to emerging trends. They also typically focus on mean estimates without addressing the full distribution of outcomes."
            },
            "audience_explanations": {
                "underwriter": "When you're underwriting a risk with limited claims history, credibility theory provides a systematic way to balance the risk's own experience with broader market data. For example, a manufacturing client with only 3 years of history might receive 30% credibility, meaning their rate is based 30% on their own claims and 70% on similar businesses in their class code. As they develop more history, the credibility assigned to their own experience increases.",
                "actuary": "Bühlmann-Straub credibility offers a rigorous framework for experience rating that accounts for both the volume of data (through exposure) and its variability (through variance components). For each class in our commercial auto rating plan, we estimate the between-variance and within-variance components to determine the optimal credibility factor. This ensures we're neither overreacting to random fluctuations in small classes nor underutilizing valuable experience data.",
                "executive": "Credibility theory allows us to maximize the value of our data across our portfolio. For large accounts with substantial experience, we can offer competitive pricing based primarily on their own performance. For smaller accounts, we maintain pricing stability by relying more heavily on class experience while still recognizing individual performance to some degree. This balanced approach helps us maintain profitability while minimizing rate disruption."
            },
            "examples": [
                {
                    "context": "Workers' Compensation Experience Rating",
                    "explanation": "A midsize employer with $1.5M in premium generates enough data to receive 75% credibility, so their experience modification factor is calculated giving 75% weight to their own loss history and 25% to expected losses for their industry classification."
                },
                {
                    "context": "Actuarial Reserving",
                    "explanation": "When estimating ultimate losses for a new cyber liability product, actuaries might assign 40% credibility to the product's limited experience and 60% to a benchmark based on similar products and industry data."
                }
            ],
            "related_concepts": ["experience rating", "bühlmann credibility", "bayesian statistics", "complement of credibility", "credibility parameter"]
        },
        {
            "concept_id": "generalized-linear-model",
            "title": "Generalized Linear Model (GLM)",
            "content": {
                "definition": "A Generalized Linear Model (GLM) is a flexible statistical modeling technique that extends linear regression to handle different types of response variables and relationships.",
                "technical_details": "GLMs consist of three components: a random component (the probability distribution of the response variable), a systematic component (the linear predictor), and a link function that connects the two. Common distributions include Gaussian, Poisson, gamma, and binomial. Common link functions include identity, log, inverse, and logit.",
                "insurance_context": "GLMs are widely used in insurance for pricing, claims modeling, and risk assessment because they can handle the non-normal distributions common in insurance data (like claim counts and sizes) while maintaining interpretability.",
                "limitations": "GLMs assume independence of observations, appropriate specification of the distribution and link function, and may struggle with highly non-linear relationships or complex interactions without explicit specification."
            },
            "audience_explanations": {
                "underwriter": "The GLM-based pricing models underlying our rating plans quantify the relationship between risk factors and expected claims. When you see that a factor has a relativty of 1.2, it means that particular characteristic is associated with 20% higher expected claims, all else being equal. Understanding these relativities helps explain to clients why certain risk characteristics result in higher premiums and guides your focus during risk inspections and mitigation recommendations.",
                "actuary": "When building GLMs for insurance pricing, we typically use a frequency-severity approach with Poisson or negative binomial models for claim counts and gamma models with log links for severity. This allows us to model the loss cost as the product of frequency and severity while accounting for the different distributional characteristics of each component. We can then incorporate credibility adjustments for classes with limited data and test various interaction terms to capture non-additive effects between rating variables.",
                "executive": "Our GLM-based rating plans give us a competitive advantage through more granular risk segmentation than traditional class-based rating. By simultaneously analyzing multiple risk factors, we can identify profitable niches within traditionally challenging classes. The interpretable nature of GLMs also helps us explain rate changes to regulators and demonstrate actuarial soundness, reducing the time to implement new rates in the market."
            },
            "examples": [
                {
                    "context": "Auto Insurance Rating",
                    "explanation": "A Poisson GLM for auto collision claim frequency might show that urban drivers have a 45% higher expected claim frequency than rural drivers, while a gamma GLM for severity might show only a 10% difference, resulting in a combined relativty of 1.6 for urban vs. rural territory."
                },
                {
                    "context": "Workers' Compensation",
                    "explanation": "A GLM analysis reveals that construction businesses with formal safety programs have 30% lower claim frequency but only 5% lower severity per claim, supporting a premium discount that reflects this difference in expected losses."
                }
            ],
            "related_concepts": ["linear regression", "poisson regression", "link function", "deviance", "multicollinearity"]
        }
    ]

    # Get the knowledge base bucket name
    bucket_name = get_bucket_name()
    print(f"Knowledge base bucket: {bucket_name}")

    # Upload each concept as a separate JSON file
    for concept in concepts:
        concept_id = concept["concept_id"]
        file_content = json.dumps(concept, indent=2)
        key = f"concepts/{concept_id}.json"
        
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=file_content,
            ContentType='application/json'
        )
        print(f"Uploaded {concept_id} to s3://{bucket_name}/{key}")

    print("Knowledge base creation completed!")

if __name__ == "__main__":
    create_knowledge_base_documents()