"""
Console email sender adapter - Implements EmailSender protocol.

This module provides a console-based implementation of the domain's
email sender port, logging verification codes to stdout for demo purposes.
"""

import logging

logger = logging.getLogger(__name__)


class ConsoleEmailSender:
    """
    Implements EmailSender protocol via console logging.

    Uses structural subtyping - no explicit inheritance from Protocol.
    For demo/development purposes - prints verification codes to stdout.
    """

    def send_verification_code(self, email: str, code: str) -> None:
        """
        Log verification code to console (simulates email delivery).

        In production, this would be replaced with an SMTP adapter.
        The code is logged at INFO level to be visible in docker-compose logs.

        Args:
            email: Recipient email address (normalized by domain layer)
            code: 4-digit verification code
        """
        logger.info("[VERIFICATION] Email: %s Code: %s", email, code)
