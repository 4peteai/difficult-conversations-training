from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Optional
from copy import deepcopy
from models.session import SessionState


class SessionManager:
    def __init__(self, session_timeout_hours: float = 1.0):
        self._sessions: Dict[str, SessionState] = {}
        self._lock = Lock()
        self._timeout = timedelta(hours=session_timeout_hours)

    def create_session(self, user_id: str) -> SessionState:
        """
        Create a new session for a user.

        Args:
            user_id: Unique identifier for the user

        Returns:
            Newly created SessionState object
        """
        with self._lock:
            session = SessionState(user_id=user_id)
            self._sessions[user_id] = session
            return session

    def get_session(self, user_id: str) -> Optional[SessionState]:
        """
        Retrieve a user's session if it exists and is not expired.

        Args:
            user_id: Unique identifier for the user

        Returns:
            SessionState object if found and valid, None otherwise
        """
        with self._lock:
            session = self._sessions.get(user_id)
            if session is None:
                return None

            if self._is_expired(session):
                del self._sessions[user_id]
                return None

            return session

    def update_session(self, user_id: str, **updates) -> Optional[SessionState]:
        """
        Update session attributes dynamically.

        Args:
            user_id: Unique identifier for the user
            **updates: Key-value pairs of attributes to update

        Returns:
            Updated SessionState object if found and valid, None otherwise
        """
        with self._lock:
            session = self._sessions.get(user_id)
            if session is None:
                return None

            if self._is_expired(session):
                del self._sessions[user_id]
                return None

            for key, value in updates.items():
                if hasattr(session, key):
                    setattr(session, key, value)

            session.update_activity()
            return session

    def delete_session(self, user_id: str) -> bool:
        """
        Delete a user's session.

        Args:
            user_id: Unique identifier for the user

        Returns:
            True if session was deleted, False if it didn't exist
        """
        with self._lock:
            if user_id in self._sessions:
                del self._sessions[user_id]
                return True
            return False

    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions.

        Returns:
            Number of sessions that were cleaned up
        """
        with self._lock:
            expired_users = [
                user_id
                for user_id, session in self._sessions.items()
                if self._is_expired(session)
            ]
            for user_id in expired_users:
                del self._sessions[user_id]
            return len(expired_users)

    def get_all_sessions(self) -> Dict[str, SessionState]:
        """
        Get all active sessions (deep copy for thread safety).

        Returns:
            Dictionary mapping user_id to SessionState
        """
        with self._lock:
            return deepcopy(self._sessions)

    def _is_expired(self, session: SessionState) -> bool:
        return datetime.utcnow() - session.last_activity > self._timeout
