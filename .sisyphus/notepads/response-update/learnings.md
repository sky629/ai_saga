Task: Add game-related game fields to UserResponse and UserWithSocialAccountsResponse.

What was done:
- Inserted three fields immediately after user_level in both UserResponse and UserWithSocialAccountsResponse:
  - game_level: int = 1
  - game_experience: int = 0
  - game_current_experience: int = 0
- Verified existence via runtime check:
  - Command: uv run python -c "from app.auth.presentation.routes.schemas.response import UserResponse; r = UserResponse.__fields__; print('game_level' in r, 'game_experience' in r)"
  - Result: True True

Notes:
- No existing fields were renamed or removed; only additions were made after user_level to keep grouping consistent.
- The patch preserves import structure and should be compatible with existing usage.

Follow-up:
- If there are any tests referencing field lists or JSON schemas, consider updating to include the new fields where appropriate.
