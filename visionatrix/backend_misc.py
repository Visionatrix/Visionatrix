from fastapi import HTTPException, Request, status


def _require_admin(request: Request) -> None:
    if not request.scope["user_info"].is_admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin privilege required") from None
