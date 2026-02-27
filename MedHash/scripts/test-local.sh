#!/bin/bash

echo "🔧 MedHash Local Test Suite"
echo "==========================="

# Test 1: SAM Local API
echo "📡 Starting SAM local API..."
sam local start-api -d 3001 --template backend/template.yaml &
SAM_PID=$!

sleep 5

# Test 2: Fetch PubMed
echo "📚 Testing PubMed fetch..."
curl -X POST http://localhost:3001/fetch \
  -H "Content-Type: application/json" \
  -d '{"pmid":"12345678"}'

echo "\n\n"

# Test 3: Start Frontend
echo "🎨 Starting Next.js frontend..."
cd frontend && npm run dev &
NEXT_PID=$!

echo "\n✅ All services started!"
echo "📱 Frontend: http://localhost:3000"
echo "🔌 API: http://localhost:3001"
echo "\nPress Ctrl+C to stop all services"

wait