import pytest
from datetime import datetime, timedelta
from threading import Thread
from time import sleep
from services.session_manager import SessionManager
from models.session import SessionState


@pytest.fixture
def manager():
    return SessionManager(session_timeout_hours=1.0)


@pytest.fixture
def short_timeout_manager():
    return SessionManager(session_timeout_hours=0.0001)


class TestSessionCreation:
    def test_create_session(self, manager):
        session = manager.create_session("user123")
        assert session is not None
        assert session.user_id == "user123"
        assert session.current_step == 1
        assert session.failure_count == 0
        assert session.in_remediation is False
        assert session.completed is False

    def test_create_multiple_sessions(self, manager):
        session1 = manager.create_session("user1")
        session2 = manager.create_session("user2")
        assert session1.user_id == "user1"
        assert session2.user_id == "user2"

    def test_create_session_overwrites_existing(self, manager):
        session1 = manager.create_session("user123")
        manager.update_session("user123", current_step=3)
        session2 = manager.create_session("user123")
        assert session2.current_step == 1


class TestSessionRetrieval:
    def test_get_existing_session(self, manager):
        created = manager.create_session("user123")
        retrieved = manager.get_session("user123")
        assert retrieved is not None
        assert retrieved.user_id == created.user_id

    def test_get_nonexistent_session(self, manager):
        session = manager.get_session("nonexistent")
        assert session is None

    def test_get_expired_session_returns_none(self, short_timeout_manager):
        short_timeout_manager.create_session("user123")
        sleep(0.5)
        session = short_timeout_manager.get_session("user123")
        assert session is None


class TestSessionUpdate:
    def test_update_session_fields(self, manager):
        manager.create_session("user123")
        updated = manager.update_session(
            "user123", current_step=3, failure_count=1, in_remediation=True
        )
        assert updated is not None
        assert updated.current_step == 3
        assert updated.failure_count == 1
        assert updated.in_remediation is True

    def test_update_nonexistent_session(self, manager):
        result = manager.update_session("nonexistent", current_step=2)
        assert result is None

    def test_update_invalid_field_ignored(self, manager):
        manager.create_session("user123")
        updated = manager.update_session("user123", invalid_field="value")
        assert updated is not None
        assert not hasattr(updated, "invalid_field")

    def test_update_refreshes_activity(self, manager):
        manager.create_session("user123")
        sleep(0.1)
        before_update = manager.get_session("user123").last_activity
        sleep(0.1)
        manager.update_session("user123", current_step=2)
        after_update = manager.get_session("user123").last_activity
        assert after_update > before_update

    def test_update_expired_session_returns_none(self, short_timeout_manager):
        short_timeout_manager.create_session("user123")
        sleep(0.5)
        result = short_timeout_manager.update_session("user123", current_step=2)
        assert result is None


class TestSessionDeletion:
    def test_delete_existing_session(self, manager):
        manager.create_session("user123")
        result = manager.delete_session("user123")
        assert result is True
        assert manager.get_session("user123") is None

    def test_delete_nonexistent_session(self, manager):
        result = manager.delete_session("nonexistent")
        assert result is False


class TestSessionExpiration:
    def test_cleanup_expired_sessions(self, short_timeout_manager):
        short_timeout_manager.create_session("user1")
        short_timeout_manager.create_session("user2")
        short_timeout_manager.create_session("user3")
        sleep(0.5)
        count = short_timeout_manager.cleanup_expired_sessions()
        assert count == 3
        assert short_timeout_manager.get_session("user1") is None

    def test_cleanup_mixed_sessions(self, short_timeout_manager):
        short_timeout_manager.create_session("old_user")
        sleep(0.5)
        short_timeout_manager.create_session("new_user")
        count = short_timeout_manager.cleanup_expired_sessions()
        assert count == 1
        assert short_timeout_manager.get_session("old_user") is None
        assert short_timeout_manager.get_session("new_user") is not None


class TestConcurrency:
    def test_concurrent_creates(self, manager):
        def create_sessions(start_id):
            for i in range(10):
                manager.create_session(f"user_{start_id}_{i}")

        threads = [Thread(target=create_sessions, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        all_sessions = manager.get_all_sessions()
        assert len(all_sessions) == 50

    def test_concurrent_updates(self, manager):
        manager.create_session("shared_user")

        def update_step():
            for _ in range(10):
                session = manager.get_session("shared_user")
                if session:
                    manager.update_session(
                        "shared_user", current_step=session.current_step
                    )

        threads = [Thread(target=update_step) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        session = manager.get_session("shared_user")
        assert session is not None

    def test_concurrent_read_write(self, manager):
        manager.create_session("test_user")
        results = []

        def reader():
            for _ in range(20):
                session = manager.get_session("test_user")
                results.append(session is not None)

        def writer():
            for i in range(10):
                manager.update_session("test_user", current_step=i % 5 + 1)

        read_threads = [Thread(target=reader) for _ in range(3)]
        write_threads = [Thread(target=writer) for _ in range(2)]

        for t in read_threads + write_threads:
            t.start()
        for t in read_threads + write_threads:
            t.join()

        assert all(results)


class TestGetAllSessions:
    def test_get_all_sessions_returns_copy(self, manager):
        manager.create_session("user1")
        manager.create_session("user2")

        sessions = manager.get_all_sessions()
        assert len(sessions) == 2

        sessions["user1"].current_step = 99

        original = manager.get_session("user1")
        assert original.current_step != 99

    def test_get_all_sessions_empty(self, manager):
        sessions = manager.get_all_sessions()
        assert sessions == {}


class TestSessionStateIntegration:
    def test_add_answer_through_update(self, manager):
        manager.create_session("user123")
        session = manager.get_session("user123")
        session.add_answer(step_id=1, answer="C", correct=True)

        updated_session = manager.get_session("user123")
        assert len(updated_session.history) == 1
        assert updated_session.history[0].step_id == 1
        assert updated_session.history[0].correct is True

    def test_enter_remediation_workflow(self, manager):
        manager.create_session("user123")
        session = manager.get_session("user123")
        test_options = {"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"}
        session.enter_remediation(
            content="You missed this concept...",
            question="Try this simpler version",
            options=test_options,
            correct_answer="B",
        )

        updated = manager.get_session("user123")
        assert updated.in_remediation is True
        assert updated.remediation_content == "You missed this concept..."
        assert updated.remediation_options == test_options
        assert updated.remediation_correct_answer == "B"
        assert updated.original_step == 1

    def test_complete_session_workflow(self, manager):
        manager.create_session("user123")
        manager.update_session("user123", current_step=5)
        session = manager.get_session("user123")
        session.mark_completed()

        final = manager.get_session("user123")
        assert final.completed is True
        assert final.completed_at is not None
