"""Counsellor hand-off notifier adapters (Phase 14).

One ``Notifier`` interface, three implementations selected by
``settings.notifier_provider``:

* ``ConsoleNotifier``  - logs the hand-off (dev/test default, no external call).
* ``SmsStubNotifier``  - pretends to send an SMS; never hits a real gateway.
* ``WhatsAppLinkNotifier`` - builds a ``wa.me`` deep link for the counsellor.

The default provider is ``console`` so the whole suite runs offline with no
credentials (RULES: no hard-coded secrets, tests pass without an API key).
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.human import Escalation

logger = get_logger("kaushalpath.notifier")


def _normalise_phone(phone: str | None) -> str:
    """Keep digits only and prepend India's country code when a bare 10-digit
    number is given. Never raises - an empty result simply means no link."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10:
        digits = f"91{digits}"
    return digits


class Notifier(ABC):
    """Deliver a human-escalation hand-off to the assigned counsellor."""

    @abstractmethod
    def notify(self, escalation: Escalation) -> dict[str, str]:
        """Send the hand-off and return a small delivery receipt."""


class ConsoleNotifier(Notifier):
    def notify(self, escalation: Escalation) -> dict[str, str]:
        logger.info(
            "ESCALATION hand-off id=%s student=%s status=%s channel=%s priority=%s",
            escalation.id,
            escalation.student_id,
            escalation.status,
            escalation.channel,
            escalation.priority,
        )
        return {"provider": "console", "status": "logged"}


class SmsStubNotifier(Notifier):
    """Stub SMS gateway: validates a recipient exists but sends nothing."""

    def notify(self, escalation: Escalation) -> dict[str, str]:
        to = _normalise_phone(escalation.contact_phone)
        status = "queued" if to else "skipped-no-phone"
        logger.info("SMS-stub to=%s escalation=%s -> %s", to or "-", escalation.id, status)
        return {"provider": "sms_stub", "status": status, "to": to}


class WhatsAppLinkNotifier(Notifier):
    """Builds a wa.me deep-link the counsellor can tap to reach the family."""

    def notify(self, escalation: Escalation) -> dict[str, str]:
        to = _normalise_phone(escalation.contact_phone)
        link = f"https://wa.me/{to}" if to else ""
        logger.info("WhatsApp link escalation=%s -> %s", escalation.id, link or "(no phone)")
        status = "link_created" if link else "skipped-no-phone"
        return {"provider": "whatsapp", "status": status, "link": link}


_PROVIDERS: dict[str, type[Notifier]] = {
    "console": ConsoleNotifier,
    "sms_stub": SmsStubNotifier,
    "whatsapp": WhatsAppLinkNotifier,
}


def get_notifier(provider: str | None = None) -> Notifier:
    """Return the notifier for ``provider`` (default: from settings)."""
    name = (provider or get_settings().notifier_provider or "console").lower()
    cls = _PROVIDERS.get(name, ConsoleNotifier)
    return cls()
