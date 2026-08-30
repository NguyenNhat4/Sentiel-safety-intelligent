import httpx


class TelegramNotificationAdapter:
    """Provider adapter for Telegram Bot API text delivery."""

    def __init__(self, bot_token: str, timeout_seconds: float = 5.0) -> None:
        self._bot_token = bot_token.strip()
        self._timeout_seconds = timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self._bot_token)

    async def send_message(self, chat_id: str, text: str) -> None:
        if not self.configured:
            return
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{self._bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
            )
            response.raise_for_status()

    def bot_username(self) -> str:
        if not self.configured:
            raise RuntimeError("Telegram bot is not configured")
        response = httpx.get(f"https://api.telegram.org/bot{self._bot_token}/getMe", timeout=self._timeout_seconds)
        response.raise_for_status()
        username = response.json().get("result", {}).get("username")
        if not isinstance(username, str) or not username:
            raise RuntimeError("Telegram bot username is unavailable")
        return username

    def start_messages(self) -> list[tuple[str, str, str | None]]:
        if not self.configured:
            raise RuntimeError("Telegram bot is not configured")
        response = httpx.get(
            f"https://api.telegram.org/bot{self._bot_token}/getUpdates",
            params={"allowed_updates": '["message"]'},
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        matches: list[tuple[str, str, str | None]] = []
        for update in response.json().get("result", []):
            message = update.get("message") or {}
            text = message.get("text")
            if not isinstance(text, str) or not text.startswith("/start "):
                continue
            chat_id = message.get("chat", {}).get("id")
            if isinstance(chat_id, int):
                sender = message.get("from", {}).get("username")
                matches.append(
                    (text.removeprefix("/start "), str(chat_id), sender if isinstance(sender, str) else None)
                )
        return matches
