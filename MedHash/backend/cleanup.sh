#!/bin/bash

# MedHash Cleanup Script
echo "🧹 Cleaning up MedHash AWS Resources"

ENVIRONMENT=${1:-dev}
STACK_NAME="medhash-$ENVIRONMENT"

print_status() {
    echo -e "\033[0;34m[INFO]\033[0m $1"
}

print_success() {
    echo -e "\033[0;32m[SUCCESS]\033[0m $1"
}

print_error() {
    echo -e "\033[0;31m[ERROR]\033[0m $1"
}

print_warning() {
    echo -e "\033[1;33m[WARNING]\033[0m $1"
}

# Confirm deletion
read -p "Are you sure you want to delete stack $STACK_NAME? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_status "Cleanup cancelled"
    exit 0
fi

# Delete CloudFormation stack
print_status "Deleting stack: $STACK_NAME"
aws cloudformation delete-stack --stack-name "$STACK_NAME"

if [ $? -eq 0 ]; then
    print_status "Waiting for stack deletion to complete..."
    aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME"
    print_success "Stack deleted successfully"
else
    print_error "Failed to delete stack"
fi

# List remaining log groups
print_status "Checking for leftover log groups..."
LOG_GROUPS=$(aws logs describe-log-groups \
    --log-group-name-prefix "/aws/lambda/medhash" \
    --query "logGroups[].logGroupName" \
    --output text)

if [ -n "$LOG_GROUPS" ]; then
    print_warning "Found leftover log groups:"
    echo "$LOG_GROUPS"
    
    read -p "Delete all medhash log groups? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        for LOG_GROUP in $LOG_GROUPS; do
            print_status "Deleting $LOG_GROUP"
            aws logs delete-log-group --log-group-name "$LOG_GROUP"
        done
        print_success "Log groups deleted"
    fi
fi

print_success "✅ Cleanup complete!"