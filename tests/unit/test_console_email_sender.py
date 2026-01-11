"""
Unit tests for ConsoleEmailSender adapter.

Tests verify the console email sender implements EmailSender protocol
and logs verification codes in the correct format.
"""

import logging
from concurrent.futures import ThreadPoolExecutor

import pytest

from src.adapters.smtp.console import ConsoleEmailSender


class TestConsoleEmailSenderProtocol:
    """Tests for EmailSender protocol compliance."""

    def test_implements_email_sender_protocol(self) -> None:
        """ConsoleEmailSender implements EmailSender protocol."""
        from src.domain.ports import EmailSender

        sender = ConsoleEmailSender()
        # Protocol check - has required method with correct signature
        assert hasattr(sender, "send_verification_code")
        assert callable(sender.send_verification_code)

        # Verify it satisfies the protocol (structural subtyping)
        def accepts_email_sender(s: EmailSender) -> None:
            pass

        # This should not raise a type error
        accepts_email_sender(sender)

    def test_no_explicit_inheritance(self) -> None:
        """ConsoleEmailSender uses structural subtyping, not inheritance."""
        # Verify the class doesn't inherit from any protocol
        # Check __bases__ to ensure no Protocol inheritance
        bases = ConsoleEmailSender.__bases__
        assert bases == (object,), f"Expected only object as base, got {bases}"


class TestSendVerificationCode:
    """Tests for send_verification_code method."""

    def test_send_verification_code_logs_message(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verification code is logged at INFO level."""
        sender = ConsoleEmailSender()

        with caplog.at_level(logging.INFO):
            sender.send_verification_code("test@example.com", "1234")

        assert len(caplog.records) == 1
        assert caplog.records[0].levelno == logging.INFO

    def test_send_verification_code_format(self, caplog: pytest.LogCaptureFixture) -> None:
        """Log format matches specification: [VERIFICATION] Email: ... Code: ..."""
        sender = ConsoleEmailSender()

        with caplog.at_level(logging.INFO):
            sender.send_verification_code("user@example.com", "5678")

        assert "[VERIFICATION]" in caplog.text
        assert "Email: user@example.com" in caplog.text
        assert "Code: 5678" in caplog.text

    def test_send_verification_code_returns_none(self) -> None:
        """Method returns None (fire-and-forget)."""
        sender = ConsoleEmailSender()
        result = sender.send_verification_code("test@example.com", "1234")
        assert result is None

    def test_send_verification_code_with_various_emails(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Method handles various email formats correctly."""
        sender = ConsoleEmailSender()
        emails = [
            "simple@example.com",
            "user.name@domain.org",
            "user+tag@example.com",
        ]

        with caplog.at_level(logging.INFO):
            for email in emails:
                sender.send_verification_code(email, "1234")

        assert len(caplog.records) == 3
        for email in emails:
            assert email in caplog.text

    def test_send_verification_code_with_various_codes(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Method handles various code formats correctly."""
        sender = ConsoleEmailSender()
        codes = ["0000", "1234", "9999", "0001"]

        with caplog.at_level(logging.INFO):
            for code in codes:
                sender.send_verification_code("test@example.com", code)

        assert len(caplog.records) == 4
        for code in codes:
            assert f"Code: {code}" in caplog.text


class TestNoSideEffects:
    """Tests verifying no side effects occur."""

    def test_no_external_connections(self) -> None:
        """Console sender makes no external connections."""
        sender = ConsoleEmailSender()
        # This should complete instantly without any network activity
        sender.send_verification_code("test@example.com", "1234")
        # If we reach here without timeout or network errors, test passes

    def test_multiple_calls_are_independent(self, caplog: pytest.LogCaptureFixture) -> None:
        """Multiple calls don't affect each other."""
        sender = ConsoleEmailSender()

        with caplog.at_level(logging.INFO):
            sender.send_verification_code("first@example.com", "1111")
            sender.send_verification_code("second@example.com", "2222")

        assert len(caplog.records) == 2
        assert "first@example.com" in caplog.text
        assert "second@example.com" in caplog.text
        assert "1111" in caplog.text
        assert "2222" in caplog.text


class TestThreadSafety:
    """Tests for thread-safe logging."""

    def test_concurrent_logging_is_thread_safe(self, caplog: pytest.LogCaptureFixture) -> None:
        """Multiple concurrent calls don't corrupt log output."""
        sender = ConsoleEmailSender()
        emails = [f"user{i}@example.com" for i in range(10)]
        codes = [f"{i:04d}" for i in range(10)]

        with caplog.at_level(logging.INFO), ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(sender.send_verification_code, email, code)
                for email, code in zip(emails, codes, strict=True)
            ]
            for f in futures:
                f.result()

        # All 10 messages should be logged
        assert len(caplog.records) == 10

        # Each message should be complete (not interleaved)
        for record in caplog.records:
            assert "[VERIFICATION]" in record.message
            assert "Email:" in record.message
            assert "Code:" in record.message

    def test_concurrent_calls_all_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        """All concurrent calls produce log entries."""
        sender = ConsoleEmailSender()

        with caplog.at_level(logging.INFO), ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(sender.send_verification_code, f"user{i}@example.com", f"{i:04d}")
                for i in range(5)
            ]
            for f in futures:
                f.result()

        # Verify all 5 messages logged
        assert len(caplog.records) == 5
