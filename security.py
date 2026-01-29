"""
Security layer for payload signing, verification codes, and secure communication
Ensures trade payloads from Lua are authentic and trades are secure
"""

import hmac
import hashlib
import secrets
import string
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple


class SecurityManager:
    """Handles secure payload signing and verification codes"""
    
    # Word list for generating verification codes (like PHP version)
    CODE_WORDS = [
        "monday", "tuesday", "wednesday", "thursday", "friday",
        "saturday", "sunday", "caramel", "fun", "files", "gate",
        "heart", "keep", "gravity", "farewell", "plastic"
    ]
    
    CODE_LENGTH = 16  # 16 words like PHP version
    CODE_SEPARATOR = " "
    
    def __init__(self, api_secret: str):
        """
        Initialize security manager
        
        Args:
            api_secret: Secret key for HMAC signing
        """
        self.api_secret = api_secret.encode()
    
    def generate_verification_code(self) -> str:
        """
        Generate a random verification code (like PHP version)
        User puts this code in their Roblox bio to verify ownership
        
        Returns:
            Verification code (e.g., "monday friday caramel...")
        """
        code = [secrets.choice(self.CODE_WORDS) for _ in range(self.CODE_LENGTH)]
        return self.CODE_SEPARATOR.join(code)
    
    def sign_payload(self, payload: Dict, timestamp: float = None) -> Dict:
        """
        Sign a payload for Lua to send to API
        Lua will include this signature in requests
        
        Args:
            payload: Data dict to sign
            timestamp: Unix timestamp (current time if not provided)
        
        Returns:
            Payload with added signature
        """
        if timestamp is None:
            timestamp = datetime.utcnow().timestamp()
        
        payload_with_timestamp = {**payload, "timestamp": timestamp}
        
        # Create signature from payload
        import json
        payload_str = json.dumps(payload_with_timestamp, sort_keys=True, separators=(',', ':'))
        signature = hmac.new(
            self.api_secret,
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        payload_with_timestamp["signature"] = signature
        return payload_with_timestamp
    
    def verify_payload(self, payload: Dict, max_age_seconds: int = 300) -> Tuple[bool, Optional[str]]:
        """
        Verify a payload signature from Lua
        
        Args:
            payload: Payload dict with signature
            max_age_seconds: Maximum age of payload (prevent replay attacks)
        
        Returns:
            (is_valid, error_message)
        """
        if "signature" not in payload:
            return False, "Missing signature"
        
        if "timestamp" not in payload:
            return False, "Missing timestamp"
        
        # Extract signature and verify it wasn't tampered with
        provided_signature = payload.pop("signature")
        
        # Recreate signature
        import json
        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        expected_signature = hmac.new(
            self.api_secret,
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Secure comparison to prevent timing attacks
        if not hmac.compare_digest(provided_signature, expected_signature):
            return False, "Invalid signature"
        
        # Check timestamp isn't too old (prevent replay attacks)
        timestamp = payload.get("timestamp")
        current_time = datetime.utcnow().timestamp()
        age = current_time - timestamp
        
        if age > max_age_seconds:
            return False, f"Payload too old ({age}s > {max_age_seconds}s)"
        
        if age < 0:  # Timestamp in future
            return False, "Invalid timestamp (future)"
        
        return True, None
    
    def create_trade_payload(self, user_id: int, items: list, trade_type: str) -> Dict:
        """
        Create a signed trade payload for Lua bot to send
        
        Args:
            user_id: Roblox user ID of trader
            items: List of items with name and quantity
            trade_type: "deposit" or "withdraw"
        
        Returns:
            Signed payload ready to send from Lua
        """
        payload = {
            "userId": user_id,
            "items": items,
            "type": trade_type,
            "game": "MM2"
        }
        
        return self.sign_payload(payload)
    
    def create_verification_challenge(self, discord_id: int, roblox_user_id: int) -> Dict:
        """
        Create a verification challenge (code user must put in bio)
        
        Returns:
            Challenge data with code
        """
        code = self.generate_verification_code()
        
        return {
            "code": code,
            "message": f"Please put this code in your Roblox bio to verify: {code}",
            "discord_id": discord_id,
            "roblox_user_id": roblox_user_id,
            "created_at": datetime.utcnow().isoformat()
        }
    
    def is_valid_username(self, username: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Roblox username format
        (ported from PHP login.php)
        
        Returns:
            (is_valid, error_message)
        """
        if len(username) < 3:
            return False, "Username is too short"
        
        if len(username) > 20:
            return False, "Username is too long"
        
        # Only alphanumeric and underscore
        if not all(c.isalnum() or c == '_' for c in username):
            return False, "Username contains invalid characters"
        
        # Can't start with underscore
        if username.startswith('_'):
            return False, "Username cannot start with underscore"
        
        # Can't end with underscore
        if username.endswith('_'):
            return False, "Username cannot end with underscore"
        
        # Max 2 underscore-separated parts (one underscore max)
        if username.count('_') > 1:
            return False, "Username can contain at most one underscore"
        
        return True, None
