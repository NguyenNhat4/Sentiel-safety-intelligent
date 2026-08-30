import datetime
import hashlib
import secrets

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.integrations.telegram_notifications import TelegramNotificationAdapter
from backend.app.models.user import TelegramLinkChallenge, User, utc_now


class TelegramLinkError(Exception):
    pass


class TelegramLinkService:
    def __init__(self, db: Session, adapter: TelegramNotificationAdapter | None = None) -> None:
        self.db = db
        settings = get_settings()
        self.adapter = adapter or TelegramNotificationAdapter(
            settings.telegram_bot_token, settings.telegram_request_timeout_seconds
        )
        self.ttl = datetime.timedelta(seconds=settings.telegram_link_ttl_seconds)

    def start(self, user_id: str) -> tuple[str, datetime.datetime]:
        try:
            if not self.db.get(User, user_id):
                raise TelegramLinkError("Account not found")
            secret = secrets.token_urlsafe(24)
            expires_at = utc_now() + self.ttl
            self.db.query(TelegramLinkChallenge).filter(
                TelegramLinkChallenge.user_id == user_id, TelegramLinkChallenge.consumed_at.is_(None)
            ).update({TelegramLinkChallenge.consumed_at: utc_now()})
            self.db.add(TelegramLinkChallenge(user_id=user_id, secret_digest=_digest(secret), expires_at=expires_at))
            self.db.commit()
            return f"https://t.me/{self.adapter.bot_username()}?start={secret}", expires_at
        except TelegramLinkError:
            raise
        except (SQLAlchemyError, httpx.HTTPError, RuntimeError) as exc:
            self.db.rollback()
            raise TelegramLinkError("Could not start Telegram linking") from exc

    def complete(self, user_id: str) -> tuple[str, str | None, str | None]:
        try:
            challenge = (
                self.db.query(TelegramLinkChallenge)
                .filter(
                    TelegramLinkChallenge.user_id == user_id,
                    TelegramLinkChallenge.consumed_at.is_(None),
                    TelegramLinkChallenge.expires_at > utc_now(),
                )
                .order_by(TelegramLinkChallenge.created_at.desc())
                .first()
            )
            if challenge is None:
                return "expired", None, None
            for payload, chat_id, username in self.adapter.start_messages():
                if not secrets.compare_digest(challenge.secret_digest, _digest(payload)):
                    continue
                user = self.db.get(User, user_id)
                if user is None:
                    raise TelegramLinkError("Account not found")
                user.telegram_chat_id = chat_id
                user.telegram_username = f"@{username}" if username else None
                challenge.consumed_at = utc_now()
                self.db.commit()
                return "linked", chat_id, user.telegram_username
            return "pending", None, None
        except (SQLAlchemyError, httpx.HTTPError, RuntimeError) as exc:
            self.db.rollback()
            raise TelegramLinkError("Could not check Telegram linking") from exc


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
