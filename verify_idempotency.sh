#!/bin/bash

# Configuration
API_URL="http://localhost:8000/api/v1"
USERNAME="testuser"
PASSWORD="testpassword"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "=================================================="
echo "      AI Saga Idempotency Verification Script"
echo "=================================================="

# 1. Get Token
echo ""
echo "[1] Getting Access Token..."
TOKEN=$(curl -s -X POST "$API_URL/dev/token" -H "Content-Type: application/json" -d '{}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "Token: ${TOKEN:0:10}..."

# 2. Setup (Scenario & Character)
echo ""
echo "[2] Setting up Game Session..."

# Seed Scenarios (Idempotent)
echo "Seeding Scenarios..."
curl -s -X POST "$API_URL/dev/seed-scenarios" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" > /dev/null

# Get Scenario
SCENARIO_ID=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/game/scenarios" | python3 -c "import sys, json; print(json.load(sys.stdin)[0]['id'])")
echo "Scenario: $SCENARIO_ID"

# Create Character
CHAR_NAME="IdempotencyTester_$(date +%s)"
CHAR_ID=$(curl -s -X POST "$API_URL/game/characters" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$CHAR_NAME\", \"description\": \"Tester\"}" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Character: $CHAR_ID"

# Start Game
SESSION_ID=$(curl -s -X POST "$API_URL/game/sessions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"character_id\": \"$CHAR_ID\", \"scenario_id\": \"$SCENARIO_ID\", \"max_turns\": 5}" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Session ID: $SESSION_ID"

# 3. Test Idempotency
REQ_ID="req_$(date +%s)_$RANDOM"
echo ""
echo "[3] Preparing Idempotency Test (Waiting 20s for rate limit safety)..."
sleep 20

echo "[4] Sending Request A (First Time) with Request ID: $REQ_ID"
echo "Waiting for LLM..."
START_TIME=$(date +%s)
RESP_A=$(curl -s -X POST "$API_URL/game/sessions/$SESSION_ID/actions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $REQ_ID" \
  -d "{\"action\": \"Look around\"}")
END_TIME=$(date +%s)
DURATION_A=$((END_TIME - START_TIME))
echo "Response A received in ${DURATION_A}s"

# Validation
if [[ $RESP_A != *"turn_count"* ]]; then
    echo -e "${RED}FAILURE: Request A failed. Response:${NC}"
    echo "$RESP_A"
    exit 1
fi

TURN_A=$(echo $RESP_A | python3 -c "import sys, json; print(json.load(sys.stdin)['turn_count'])")
MSG_A=$(echo $RESP_A | python3 -c "import sys, json; print(json.load(sys.stdin)['narrative'][:20])")
echo "Turn: $TURN_A, Narrative: $MSG_A..."

echo ""
echo "[4] Sending Request B (Duplicate) with SAME Request ID: $REQ_ID"
START_TIME=$(date +%s)
RESP_B=$(curl -s -X POST "$API_URL/game/sessions/$SESSION_ID/actions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $REQ_ID" \
  -d "{\"action\": \"Look around\"}")
END_TIME=$(date +%s)
DURATION_B=$((END_TIME - START_TIME))
echo "Response B received in ${DURATION_B}s (Should be instant)"

# 4. Compare
echo ""
echo "[5] Verifying Identity..."
if [ "$RESP_A" == "$RESP_B" ]; then
    echo -e "${GREEN}SUCCESS: Responses are IDENTICAL.${NC}"
else
    echo -e "${RED}FAILURE: Responses differ.${NC}"
    echo "A: $RESP_A"
    echo "B: $RESP_B"
    exit 1
fi

if [ $DURATION_B -lt 2 ]; then
     echo -e "${GREEN}SUCCESS: Second request was fast ($DURATION_B sec). Cache Hit!${NC}"
else
     echo -e "${RED}WARNING: Second request took long ($DURATION_B sec). Cache Miss?${NC}"
fi

# Cleanup
curl -s -X DELETE "$API_URL/game/sessions/$SESSION_ID" \
  -H "Authorization: Bearer $TOKEN" > /dev/null
