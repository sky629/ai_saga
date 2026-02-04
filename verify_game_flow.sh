#!/bin/bash
# verify_game_flow.sh

echo "=================================================="
echo "      AI Saga Game Flow Verification ScriptStart"
echo "=================================================="

# 1. Get Token
echo "[1] Getting Access Token..."
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/dev/token -H "Content-Type: application/json" -d '{}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "Token: ${TOKEN:0:10}..."

# 2. Get Scenario
echo ""
echo "[2] Getting Scenario..."
SCENARIO_ID=$(curl -s -X GET 'http://localhost:8000/api/v1/game/scenarios' -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['id'] if d else '')")
echo "Scenario ID: $SCENARIO_ID"

# 3. Create Character
echo ""
echo "[3] Creating Character..."
CHAR_RESP=$(curl -s -X POST 'http://localhost:8000/api/v1/game/characters' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "VisibleTester", "description": "Verification User"}')
CHAR_ID=$(echo "$CHAR_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Character Created: $CHAR_ID"

# 4. Start Game (3 Turns)
echo ""
echo "[4] Starting Game (Max Turns: 3)..."
SESSION_RESP=$(curl -s -X POST 'http://localhost:8000/api/v1/game/sessions' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"character_id\": \"$CHAR_ID\", \"scenario_id\": \"$SCENARIO_ID\", \"max_turns\": 3}")
echo "  ...waiting 30s (Rate Limit Prevention)..."
sleep 30

# Check for error
if [[ $SESSION_RESP == *"Internal server error"* ]] || [[ $SESSION_RESP == *"detail"* ]]; then
  echo "ERROR Starting Game:"
  echo "$SESSION_RESP"
  exit 1
fi

SESSION_ID=$(echo "$SESSION_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Session Started: $SESSION_ID"

# 5. Play Turns
echo ""
echo "[5] Playing Turns..."

echo "  -> Turn 1: Look around"
curl -s -X POST "http://localhost:8000/api/v1/game/sessions/$SESSION_ID/actions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: req_$(date +%s)_$RANDOM" \
  -d '{"action": "Look around"}' > /dev/null
echo "  ...waiting 30s (Rate Limit Prevention)..."
sleep 30

echo "  -> Turn 2: Check map"
curl -s -X POST "http://localhost:8000/api/v1/game/sessions/$SESSION_ID/actions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: req_$(date +%s)_$RANDOM" \
  -d '{"action": "Check map"}' > /dev/null
echo "  ...waiting 30s (Rate Limit Prevention)..."
sleep 30

echo "  -> Turn 3: Wait (Should trigger ending)"
ENDING_RESP=$(curl -s -X POST "http://localhost:8000/api/v1/game/sessions/$SESSION_ID/actions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: req_$(date +%s)_$RANDOM" \
  -d '{"action": "Wait"}')

echo ""
echo "Ending Response:"
echo "$ENDING_RESP" | python3 -m json.tool

# 6. Verify History (Session should still exist)
echo ""
echo "[6] Verifying History (Ended session should be in list)..."
LIST_RESP=$(curl -s -X GET "http://localhost:8000/api/v1/game/sessions" -H "Authorization: Bearer $TOKEN")
FOUND=$(echo "$LIST_RESP" | python3 -c "import sys,json; data=json.load(sys.stdin); print('YES' if any(s['id'] == '$SESSION_ID' for s in data.get('items', [])) else 'NO')")
STATUS=$(echo "$LIST_RESP" | python3 -c "import sys,json; data=json.load(sys.stdin); sess=next((s for s in data.get('items', []) if s['id'] == '$SESSION_ID'), {}); print(sess.get('status', 'NOT_FOUND'))")

echo "Session Found in List? $FOUND"
echo "Session Status: $STATUS"

# 7. Hard Delete
echo ""
echo "[7] Hard Deleting Session..."
DEL_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "http://localhost:8000/api/v1/game/sessions/$SESSION_ID" -H "Authorization: Bearer $TOKEN")
echo "Delete Response Code: $DEL_CODE"

# 8. Verify Deletion
echo ""
echo "[8] Verifying Deletion (Session should be gone)..."
LIST_AFTER=$(curl -s -X GET "http://localhost:8000/api/v1/game/sessions" -H "Authorization: Bearer $TOKEN")
FOUND_AFTER=$(echo "$LIST_AFTER" | python3 -c "import sys,json; data=json.load(sys.stdin); print('YES' if any(s['id'] == '$SESSION_ID' for s in data.get('items', [])) else 'NO')")

echo "Session Found in List? $FOUND_AFTER"

echo ""
echo "=================================================="
if [ "$FOUND" == "YES" ] && [ "$STATUS" == "ended" ] && [ "$DEL_CODE" == "204" ] && [ "$FOUND_AFTER" == "NO" ]; then
    echo "✅ VERIFICATION SUCCESSFUL"
else
    echo "❌ VERIFICATION FAILED"
fi
echo "=================================================="
