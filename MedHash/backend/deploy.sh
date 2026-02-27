#!/bin/bash

# MedHash Deployment Script
echo "🚀 Deploying MedHash Backend to AWS"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
STACK_NAME="medhash-dev"
REGION="us-east-1"
S3_BUCKET="medhash-deployment-$(aws sts get-caller-identity --query Account --output text)"
ENVIRONMENT=${1:-dev}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not found. Please install it first."
    exit 1
fi

# Check SAM CLI
if ! command -v sam &> /dev/null; then
    print_error "SAM CLI not found. Please install it first."
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured or expired."
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
print_status "AWS Account: $ACCOUNT_ID"
print_status "Region: $REGION"
print_status "Environment: $ENVIRONMENT"

# Create deployment bucket if it doesn't exist
print_status "Checking deployment bucket..."
if ! aws s3 ls "s3://$S3_BUCKET" 2>&1 > /dev/null; then
    print_status "Creating deployment bucket: $S3_BUCKET"
    aws s3 mb "s3://$S3_BUCKET" --region $REGION
else
    print_status "Deployment bucket exists: $S3_BUCKET"
fi

# Build the application
print_status "Building SAM application..."
sam build --template template.yaml

if [ $? -ne 0 ]; then
    print_error "Build failed"
    exit 1
fi

# Deploy
print_status "Deploying to AWS..."
sam deploy \
    --stack-name "medhash-$ENVIRONMENT" \
    --s3-bucket "$S3_BUCKET" \
    --s3-prefix "medhash-$ENVIRONMENT" \
    --region "$REGION" \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides "Environment=$ENVIRONMENT" \
    --no-fail-on-empty-changeset

if [ $? -eq 0 ]; then
    print_success "Deployment successful!"
    
    # Get outputs
    print_status "Getting stack outputs..."
    aws cloudformation describe-stacks \
        --stack-name "medhash-$ENVIRONMENT" \
        --query "Stacks[0].Outputs" \
        --output table
    
    # Get API endpoint
    API_ENDPOINT=$(aws cloudformation describe-stacks \
        --stack-name "medhash-$ENVIRONMENT" \
        --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
        --output text)
    
    print_success "API Endpoint: $API_ENDPOINT"
    
    # Test the deployment
    print_status "Testing deployment..."
    sleep 5  # Wait for API to propagate
    
    HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "$API_ENDPOINT/health" 2>/dev/null || echo "failed")
    
    if [ "$HEALTH_CHECK" == "200" ] || [ "$HEALTH_CHECK" == "404" ]; then
        print_success "API is responding"
    else
        print_warning "Health check returned: $HEALTH_CHECK"
    fi
    
else
    print_error "Deployment failed"
    exit 1
fi

# Create budget alert
print_status "Setting up budget alerts..."
aws budgets create-budget \
    --account-id "$ACCOUNT_ID" \
    --budget file://../infrastructure/budgets.json \
    --notifications-with-subscribers file://../infrastructure/notifications.json 2>/dev/null || \
    print_warning "Budget already exists or couldn't be created"

print_success "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "  1. Update frontend .env.local with API endpoint:"
echo "     NEXT_PUBLIC_API_URL=$API_ENDPOINT"
echo "  2. Test the API:"
echo "     curl $API_ENDPOINT/health"
echo "  3. Monitor CloudWatch logs:"
echo "     aws logs describe-log-groups --log-group-name-prefix /aws/lambda/medhash"