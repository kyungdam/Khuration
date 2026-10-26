import httpx

EXPO_URL = "https://exp.host/--/api/v2/push/send"


def is_expo_token(token: str) -> bool:
    return token.startswith(("ExponentPushToken[", "ExpoPushToken["))


def send(messages: list[dict]) -> dict:
    try:
        r = httpx.post(
            EXPO_URL, json=messages, timeout=15, headers={"Accept": "application/json"}
        )
        try:
            body = r.json()
        except Exception:
            body = r.text
        return {"ok": r.is_success, "status": r.status_code, "body": body}
    except Exception as e:  # 네트워크 오류가 서버를 죽이지 않게
        return {"ok": False, "error": str(e)}
