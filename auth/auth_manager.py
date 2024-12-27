from typing import Optional, Tuple
from database.db_manager import DatabaseManager

class AuthManager:
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def login(self, username: str, password: str) -> Optional[Tuple[bool, str]]:
        """
        Authenticate user and return login status and role
        Returns: Tuple of (success: bool, role: str) or None if failed
        """
        return self.db_manager.verify_user(username, password)
    
    def register(self, username: str, password: str, role: str = "customer") -> bool:
        """Register a new user with the given role"""
        return self.db_manager.add_user(username, password, role) 