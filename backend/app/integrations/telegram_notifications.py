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
