# Keycloak User Management Directive

## Objective
Create and manage users in Keycloak for Candid Studios applications. This handles user accounts for notes.candidstudios.net and other authenticated services.

## Inputs
- `email` (required): User email address (also used as username)
- `first_name` (required): User first name
- `last_name` (required): User last name
- `role` (optional): User role - one of: `admin`, `marketing`, `photographer`, `user` (default)
- `send_verification` (optional): Whether to send verification email (default: true)

## Process

### 1. Validate Input
- Check email format is valid
- Ensure first_name and last_name are provided
- Validate role is one of the allowed values

### 2. Check for Existing User
- Search Keycloak for existing user with this email
- If found, return existing user info (don't create duplicate)

### 3. Generate Temporary Password
- Generate secure 12-character random password
- Mark as temporary so user must change on first login

### 4. Create User in Keycloak
- Use `execution/keycloak_wrapper.py` to create user
- Set user attributes (name, email, enabled status)
- Set temporary password

### 5. Assign to Groups
- Map role to Keycloak groups:
  - `admin` → admin group
  - `marketing` → marketing group
  - `photographer` → photographer group
  - `user` → user group
- Assign user to appropriate group(s)

### 6. Send Verification Email (optional)
- Trigger Keycloak email verification
- User receives email to verify their address

### 7. Return Results
Return JSON with:
```json
{
  "status": "success",
  "user_id": "keycloak_user_id",
  "email": "user@example.com",
  "temporary_password": "generated_password",
  "role": "user",
  "groups": ["user"],
  "verification_sent": true
}
```

## Tools Available
- `execution/keycloak_wrapper.py`: Keycloak API wrapper
  - `create_user(...)` - Create new user
  - `get_user_by_email(email)` - Check for existing user
  - `set_password(user_id, password, temporary)` - Set/reset password
  - `assign_user_to_group(user_id, group_name)` - Add to group
  - `send_verify_email(user_id)` - Send verification email

## Definition of Done
- [ ] Input validated
- [ ] Existing user checked (no duplicates)
- [ ] User created in Keycloak with temporary password
- [ ] User assigned to correct group(s) based on role
- [ ] Verification email sent (if requested)
- [ ] User ID and temporary password returned

## Edge Cases
- **User already exists**: Return existing user info with status "exists"
- **Invalid email format**: Return error with details
- **Group doesn't exist**: Log warning, proceed without group assignment
- **Keycloak API error**: Return error with details, don't create partial user

## Keycloak Configuration

### Server Details
- **URL**: `https://login.candidstudios.net`
- **Admin Console**: `https://login.candidstudios.net/admin`
- **Realm**: Default realm (configure in env)

### Environment Variables
```bash
KEYCLOAK_SERVER_URL=https://login.candidstudios.net
KEYCLOAK_REALM=master
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=your_admin_password
KEYCLOAK_CLIENT_ID=admin-cli
```

### Group Mappings
| Group | Description | Permissions |
|-------|-------------|-------------|
| admin | Full administrators | All access |
| marketing | Marketing team | Lead management, campaigns |
| photographer | Photographers | Calendar, assignments |
| user | Standard users | Basic access |

## Testing
```bash
# Test Keycloak connection
python -m execution.keycloak_wrapper

# Create a test user
python -c "
from execution.keycloak_wrapper import create_candid_user
result = create_candid_user('test@example.com', 'Test', 'User', 'user')
print(result)
"
```

## Dependencies
- `python-keycloak>=3.0.0` - Keycloak admin API
- `python-dotenv>=1.0.0` - Environment variables

## Notes
- Temporary passwords require users to change on first login
- Email verification requires Keycloak to be configured with SMTP
- For bulk user creation, consider using CSV import
- Existing MCP server at `C:/Users/ryanm/keycloak-mcp-server/` may be reusable
