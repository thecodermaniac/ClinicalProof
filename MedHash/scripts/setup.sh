#!/bin/bash

# MedHash Complete Setup Script
echo "🚀 Setting up MedHash Development Environment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 not found. Please install Python 3.8+"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    print_error "Node.js not found. Please install Node.js 18+"
    exit 1
fi

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not found. Installing..."
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip
    sudo ./aws/install
    rm -rf aws awscliv2.zip
fi

# Check SAM CLI
if ! command -v sam &> /dev/null; then
    print_error "SAM CLI not found. Installing..."
    # Mac
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew tap aws/tap
        brew install aws-sam-cli
    # Linux
    else
        wget https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip
        unzip aws-sam-cli-linux-x86_64.zip -d sam-install
        sudo ./sam-install/install
        rm -rf sam-install aws-sam-cli-linux-x86_64.zip
    fi
fi

# Setup backend
print_status "Setting up backend..."
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov  # Testing dependencies

print_success "Backend dependencies installed"

# Setup frontend
print_status "Setting up frontend..."
cd ../frontend
npm install
npm install --save-dev @types/node @types/react @types/react-dom typescript

print_success "Frontend dependencies installed"

# Create .env files
print_status "Creating environment files..."
cat > .env.local << EOL
NEXT_PUBLIC_API_URL=http://localhost:3001
EOL

cd ..

# Create directories if they don't exist
mkdir -p scripts tests docs

print_success "✅ MedHash setup complete!"
print_status "Next steps:"
echo "  1. Configure AWS CLI: aws configure"
echo "  2. Start backend: cd backend && sam local start-api -p 3001"
echo "  3. Start frontend: cd frontend && npm run dev"
echo "  4. Visit: http://localhost:3000"