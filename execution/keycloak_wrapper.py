"""
Keycloak user management wrapper.

Integrates with Keycloak for user authentication and management.
Can use existing keycloak-mcp-server or direct API calls.
"""

import os
import logging
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import keycloak library
KEYCLOAK_AVAILABLE = False
try:
    from keycloak import KeycloakAdmin
    from keycloak.exceptions import KeycloakError
    KEYCLOAK_AVAILABLE = True
except ImportError:
    logger.warning("python-keycloak not available. Install with: pip install python-keycloak")


class KeycloakWrapper:
    """Wrapper for Keycloak user management operations."""

    def __init__(
        self,
        server_url: Optional[str] = None,
        realm_name: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: Optional[str] = None
    ):
        """
        Initialize Keycloak admin client.

        Args:
            server_url: Keycloak server URL (default: from env)
            realm_name: Realm to manage (default: from env)
            username: Admin username (default: from env)
            password: Admin password (default: from env)
            client_id: Client ID for admin (default: from env)
        """
        self.server_url = server_url or os.getenv('KEYCLOAK_SERVER_URL', 'https://login.candidstudios.net')
        self.realm_name = realm_name or os.getenv('KEYCLOAK_REALM', 'master')
        self.username = username or os.getenv('KEYCLOAK_ADMIN_USERNAME', 'admin')
        self.password = password or os.getenv('KEYCLOAK_ADMIN_PASSWORD')
        self.client_id = client_id or os.getenv('KEYCLOAK_CLIENT_ID', 'admin-cli')

        self.admin_client = None

        if KEYCLOAK_AVAILABLE and self.password:
            self._authenticate()

    def _authenticate(self):
        """Set up Keycloak admin authentication."""
        try:
            self.admin_client = KeycloakAdmin(
                server_url=self.server_url,
                username=self.username,
                password=self.password,
                realm_name=self.realm_name,
                client_id=self.client_id,
                verify=True
            )
            logger.info(f"Authenticated to Keycloak: {self.server_url}")
        except KeycloakError as e:
            logger.error(f"Keycloak authentication failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Keycloak client: {e}")
            raise

    def create_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
        password: Optional[str] = None,
        temporary_password: bool = True,
        enabled: bool = True,
        groups: Optional[List[str]] = None,
        attributes: Optional[Dict[str, List[str]]] = None
    ) -> str:
        """
        Create a new user in Keycloak.

        Args:
            email: User email (also used as username)
            first_name: First name
            last_name: Last name
            password: Initial password (auto-generated if not provided)
            temporary_password: Whether password is temporary (must change on first login)
            enabled: Whether account is enabled
            groups: List of group names to assign
            attributes: Custom attributes (dict with list values)

        Returns:
            User ID of created user
        """
        if not self.admin_client:
            raise RuntimeError("Keycloak admin client not initialized")

        # Generate password if not provided
        if not password:
            import secrets
            import string
            password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))

        # Create user payload
        user_payload = {
            "email": email,
            "username": email,
            "firstName": first_name,
            "lastName": last_name,
            "enabled": enabled,
            "emailVerified": False,
            "credentials": [
                {
                    "type": "password",
                    "value": password,
                    "temporary": temporary_password
                }
            ]
        }

        if attributes:
            user_payload["attributes"] = attributes

        try:
            user_id = self.admin_client.create_user(user_payload)
            logger.info(f"Created Keycloak user: {email} (ID: {user_id})")

            # Assign to groups
            if groups:
                for group_name in groups:
                    self.assign_user_to_group(user_id, group_name)

            return user_id

        except KeycloakError as e:
            logger.error(f"Failed to create user {email}: {e}")
            raise

    def get_user(self, user_id: str) -> Dict[str, Any]:
        """
        Get user by ID.

        Args:
            user_id: Keycloak user ID

        Returns:
            User data
        """
        if not self.admin_client:
            raise RuntimeError("Keycloak admin client not initialized")

        try:
            return self.admin_client.get_user(user_id)
        except KeycloakError as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            raise

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Find user by email.

        Args:
            email: User email

        Returns:
            User data or None if not found
        """
        if not self.admin_client:
            raise RuntimeError("Keycloak admin client not initialized")

        try:
            users = self.admin_client.get_users(query=email)
            for user in users:
                if user.get("email") == email:
                    return user
            return None
        except KeycloakError as e:
            logger.error(f"Failed to search for user {email}: {e}")
            return None

    def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update user data.

        Args:
            user_id: Keycloak user ID
            updates: Dict of fields to update

        Returns:
            True if successful
        """
        if not self.admin_client:
            raise RuntimeError("Keycloak admin client not initialized")

        try:
            self.admin_client.update_user(user_id, updates)
            logger.info(f"Updated user {user_id}")
            return True
        except KeycloakError as e:
            logger.error(f"Failed to update user {user_id}: {e}")
            return False

    def delete_user(self, user_id: str) -> bool:
        """
        Delete a user.

        Args:
            user_id: Keycloak user ID

        Returns:
            True if successful
        """
        if not self.admin_client:
            raise RuntimeError("Keycloak admin client not initialized")

        try:
            self.admin_client.delete_user(user_id)
            logger.info(f"Deleted user {user_id}")
            return True
        except KeycloakError as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            return False

    def set_password(
        self,
        user_id: str,
        password: str,
        temporary: bool = False
    ) -> bool:
        """
        Set user password.

        Args:
            user_id: Keycloak user ID
            password: New password
            temporary: Whether password is temporary

        Returns:
            True if successful
        """
        if not self.admin_client:
            raise RuntimeError("Keycloak admin client not initialized")

        payload = {
            "type": "password",
            "value": password,
            "temporary": temporary
        }

        try:
            self.admin_client.set_user_password(user_id, password, temporary=temporary)
            logger.info(f"Set password for user {user_id}")
            return True
        except KeycloakError as e:
            logger.error(f"Failed to set password for user {user_id}: {e}")
            return False

    def get_groups(self) -> List[Dict[str, Any]]:
        """
        Get all groups in the realm.

        Returns:
            List of groups
        """
        if not self.admin_client:
            raise RuntimeError("Keycloak admin client not initialized")

        try:
            return self.admin_client.get_groups()
        except KeycloakError as e:
            logger.error(f"Failed to get groups: {e}")
            return []

    def get_group_by_name(self, group_name: str) -> Optional[Dict[str, Any]]:
        """
        Find group by name.

        Args:
            group_name: Group name

        Returns:
            Group data or None if not found
        """
        groups = self.get_groups()
        for group in groups:
            if group.get("name") == group_name:
                return group
        return None

    def assign_user_to_group(self, user_id: str, group_name: str) -> bool:
        """
        Assign user to a group.

        Args:
            user_id: Keycloak user ID
            group_name: Group name

        Returns:
            True if successful
        """
        if not self.admin_client:
            raise RuntimeError("Keycloak admin client not initialized")

        group = self.get_group_by_name(group_name)
        if not group:
            logger.warning(f"Group not found: {group_name}")
            return False

        try:
            self.admin_client.group_user_add(user_id, group["id"])
            logger.info(f"Assigned user {user_id} to group {group_name}")
            return True
        except KeycloakError as e:
            logger.error(f"Failed to assign user to group: {e}")
            return False

    def send_verify_email(self, user_id: str) -> bool:
        """
        Send email verification email to user.

        Args:
            user_id: Keycloak user ID

        Returns:
            True if successful
        """
        if not self.admin_client:
            raise RuntimeError("Keycloak admin client not initialized")

        try:
            # Keycloak requires executing actions on the user
            self.admin_client.send_update_account(user_id, ["VERIFY_EMAIL"])
            logger.info(f"Sent verification email to user {user_id}")
            return True
        except KeycloakError as e:
            logger.error(f"Failed to send verification email: {e}")
            return False


# Convenience functions for common operations
def create_candid_user(
    email: str,
    first_name: str,
    last_name: str,
    role: str = "user",
    send_verification: bool = True
) -> Dict[str, Any]:
    """
    Create a Candid Studios user with appropriate groups.

    Args:
        email: User email
        first_name: First name
        last_name: Last name
        role: Role - one of: admin, marketing, photographer, user
        send_verification: Whether to send verification email

    Returns:
        Dict with user_id, password (if generated), and status
    """
    keycloak = KeycloakWrapper()

    # Role to group mapping
    role_groups = {
        "admin": ["admin"],
        "marketing": ["marketing"],
        "photographer": ["photographer"],
        "user": ["user"]
    }

    groups = role_groups.get(role, ["user"])

    # Create user with auto-generated temporary password
    import secrets
    import string
    password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))

    try:
        user_id = keycloak.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            temporary_password=True,
            enabled=True,
            groups=groups
        )

        if send_verification:
            keycloak.send_verify_email(user_id)

        return {
            "status": "success",
            "user_id": user_id,
            "email": email,
            "temporary_password": password,
            "role": role,
            "groups": groups,
            "verification_sent": send_verification
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


if __name__ == "__main__":
    # Test the wrapper
    try:
        keycloak = KeycloakWrapper()
        if keycloak.admin_client:
            print(f"Keycloak connected: {keycloak.server_url}")
            print(f"Realm: {keycloak.realm_name}")

            groups = keycloak.get_groups()
            print(f"Available groups: {[g.get('name') for g in groups]}")
        else:
            print("Keycloak not configured. Set up environment variables.")
    except Exception as e:
        print(f"Keycloak initialization error: {e}")
