# Dice Bug Fix - Learnings

## Task: Add dice_applied extraction + state_changes filtering to GameMasterService

### Completed
- ✅ Added `extract_dice_applied(parsed: dict) -> bool` static method
- ✅ Added `filter_state_changes_on_dice_failure(state_changes: StateChanges) -> StateChanges` static method
- ✅ 8 new tests added to `TestGameMasterServiceDiceFiltering` class
- ✅ All 27 tests pass (20 existing + 8 new)

### Key Patterns Learned

#### 1. Frozen Pydantic Models & Immutability
- StateChanges is a frozen Pydantic model (`model_config = {"frozen": True}`)
- To mutate frozen models, use `model_copy(update={...})` instead of direct assignment
- This ensures immutability and creates new instances for state changes

#### 2. Safe Defaults in Extraction Methods
- `extract_dice_applied()` uses `parsed.get("dice_applied", False)` for safe default
- Prevents KeyError and provides sensible fallback when LLM doesn't include field
- Pattern: Always provide defaults for optional LLM response fields

#### 3. Selective Filtering Strategy
- `filter_state_changes_on_dice_failure()` blocks only dangerous fields on dice failure:
  - ❌ Blocks: `location` (position changes), `items_gained` (unearned rewards)
  - ✅ Preserves: `hp_change`, `items_lost`, `experience_gained`, `npcs_met`, `discoveries`
- Rationale: Damage and losses are valid consequences of failure; position/reward changes are not

#### 4. TDD Workflow Execution
- RED phase: Write 8 failing tests first (confirmed AttributeError)
- GREEN phase: Implement minimum code to pass tests
- All tests pass without refactoring needed (simple, focused methods)

#### 5. GameMasterService Pattern
- All methods are `@staticmethod` (no instance state)
- Pure domain logic with no external dependencies
- Follows existing service pattern (extract_state_changes, extract_narrative_from_parsed, etc.)

### Code Quality Notes
- Line length: 79 chars (Black formatted)
- Docstrings: Korean per AGENTS.md convention
- Type hints: Full coverage (dict, bool, StateChanges)
- No external dependencies or I/O operations

### Bug Context Addressed
- **Problem**: LLM might return invalid state_changes on dice failure (e.g., location change, items gained)
- **Solution**: Server-side guard rail filters these fields when dice_applied=False
- **Usage**: Call `extract_dice_applied()` to check roll result, then `filter_state_changes_on_dice_failure()` if needed
# Dice Bug Fix - Learnings

## Task Completed: LLM Prompt Improvement (dice_applied + dice_result_section)

### What Was Done
1. **RED Phase**: Added 3 failing tests to `tests/unit/domain/test_game_master_prompt.py`:
   - `test_system_prompt_contains_dice_applied_in_json_format` - Verifies JSON format includes `dice_applied` field
   - `test_action_prompt_contains_dice_result` - Verifies action prompt includes dice result when provided
   - `test_action_prompt_without_dice_result` - Verifies action prompt handles missing dice result gracefully

2. **GREEN Phase**: Modified `app/llm/prompts/game_master.py`:
   - **SYSTEM_PROMPT_TEMPLATE**: Added `"dice_applied": false` to JSON response format example
   - **SYSTEM_PROMPT_TEMPLATE**: Added 4 new rules for `dice_applied` field:
     - Explains when to use `true` (combat, risky actions, skills, stealth, escape)
     - Explains when to use `false` (simple movement, dialogue, observation, rest)
     - Emphasizes that when `dice_applied: true`, must follow dice result
   - **ACTION_PROMPT_TEMPLATE**: Added `{dice_result_section}` placeholder with new section header
   - **ACTION_PROMPT_TEMPLATE**: Updated instruction to emphasize following dice results
   - **build_action_prompt()**: Added `dice_result_section: str = ""` parameter
   - **GameMasterPrompt.build_action()**: Added `dice_result_section: str = ""` parameter

3. **Verification**: All 22 tests pass (19 existing + 3 new)

### Key Patterns
- Template placeholders use `{variable_name}` format
- JSON in templates uses double braces `{{` and `}}` to escape for f-string formatting
- Default parameter values (`= ""`) allow backward compatibility
- Test docstrings follow established convention in the codebase

### Bug Context Addressed
- **System Prompt**: Now includes `dice_applied` field in JSON format to signal when dice affects outcome
- **Action Prompt**: Now includes dice result section so LLM sees dice outcome in context of action
- **Combined Effect**: LLM will now:
  1. See dice result in action prompt (not just system prompt)
  2. Know whether to apply dice via `dice_applied` field
  3. Understand rules for when dice applies (combat/risky vs. routine actions)
  4. Be instructed to follow dice results when present

### Files Modified
- `app/llm/prompts/game_master.py` (4 changes: 2 templates + 2 function signatures)
- `tests/unit/domain/test_game_master_prompt.py` (3 new tests added)

### Test Results
✅ 22/22 tests passing (100%)
