#!/bin/bash
# Test webhook with sample payloads

WEBHOOK_URL="${WEBHOOK_URL:-http://localhost:8080/webhook/calendar-ghl}"
PAYLOAD_FILE="$(dirname "$0")/../tests/test_payloads.json"

echo "🧪 Testing webhook endpoint: $WEBHOOK_URL"
echo ""

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo "⚠️  jq not found. Install for formatted output: apt install jq"
    FORMAT_FLAG=""
else
    FORMAT_FLAG="| jq ."
fi

# Test 1: Lead event
echo "1️⃣ Testing lead event..."
if command -v jq &> /dev/null; then
    PAYLOAD=$(jq -c '.test_webhook_lead' "$PAYLOAD_FILE")
    curl -X POST "$WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD" \
      -s | jq .
else
    curl -X POST "$WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -d @/dev/stdin <<< "$(jq -c '.test_webhook_lead' "$PAYLOAD_FILE")" \
      -s
fi
echo ""

# Test 2: Booked event
echo "2️⃣ Testing booked event..."
if command -v jq &> /dev/null; then
    PAYLOAD=$(jq -c '.test_webhook_booked' "$PAYLOAD_FILE")
    curl -X POST "$WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD" \
      -s | jq .
else
    curl -X POST "$WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -d @/dev/stdin <<< "$(jq -c '.test_webhook_booked' "$PAYLOAD_FILE")" \
      -s
fi
echo ""

# Test 3: Minimal payload
echo "3️⃣ Testing minimal payload..."
if command -v jq &> /dev/null; then
    PAYLOAD=$(jq -c '.test_webhook_minimal' "$PAYLOAD_FILE")
    curl -X POST "$WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD" \
      -s | jq .
else
    curl -X POST "$WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -d @/dev/stdin <<< "$(jq -c '.test_webhook_minimal' "$PAYLOAD_FILE")" \
      -s
fi
echo ""

# Test health endpoint
echo "4️⃣ Testing health endpoint..."
curl -s "$WEBHOOK_URL/webhook/../health" | { command -v jq &> /dev/null && jq . || cat; }
echo ""

# Test metrics endpoint
echo "5️⃣ Testing metrics endpoint..."
curl -s "$WEBHOOK_URL/webhook/../metrics" | { command -v jq &> /dev/null && jq . || cat; }
echo ""

echo "✅ Tests complete!"
