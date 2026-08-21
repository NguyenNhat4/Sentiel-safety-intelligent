import base64
import hashlib
import hmac
import json
import time

HLS_TOKEN_TTL_SECONDS = 15 * 60


def issue_hls_access_token(
    *, secret: str, user_id: str, role: str, cameras: list[str], now: int | None = None
) -> tuple[str, int]:
    if len(secret) < 32:
        raise ValueError("HLS token signing secret must contain at least 32 characters")
    issued_at = int(time.time() if now is None else now)
    payload = {
        "sub": user_id,
        "role": role,
        "cameras": sorted(set(cameras)),
        "iat": issued_at,
        "exp": issued_at + HLS_TOKEN_TTL_SECONDS,
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).rstrip(b"=")
    signature = base64.urlsafe_b64encode(
        hmac.new(secret.encode("utf-8"), encoded, hashlib.sha256).digest()
    ).rstrip(b"=")
    return f"{encoded.decode()}.{signature.decode()}", HLS_TOKEN_TTL_SECONDS
