"""
Authentication wiring for the API.

Two independent mechanisms coexist:

* **Shared key** (``API_KEY``) — a single bearer/``X-API-Key`` secret. Always
  honoured; enough for a private single-user server.
* **Accounts** (``AUTH_ENABLED``) — per-user username/password login backed by
  :class:`~jarvis.licensing.service.LicenseService`. Clients exchange
  credentials for a bearer token at ``POST /auth/login`` and then present it as
  ``Authorization: Bearer <token>``.

This module installs the ``/auth/*`` and ``/admin/*`` routes and exposes helpers
the app uses to resolve the caller's *principal* (a stable string used to
namespace each user's sessions and memory).
"""

import hmac

from jarvis.config.settings import Settings
from jarvis.licensing import AuthError, LicenseService

#: Principal used when the caller authenticated with the shared API key.
SHARED_PRINCIPAL = "shared"


def resolve_principal(
    provided: str | None,
    settings: Settings,
    service: LicenseService | None,
) -> str | None:
    """Map a presented secret to a principal, or ``None`` if unauthorised.

    Order: a valid per-user login token wins; otherwise the shared API key.
    """
    if service is not None and provided:
        account = service.validate_token(provided)
        if account is not None:
            return f"user:{account.username}"
    if not settings.api_key:
        # Open only when no shared key is set AND accounts are not required.
        if service is None:
            return SHARED_PRINCIPAL
    elif provided is not None and hmac.compare_digest(provided, settings.api_key):
        return SHARED_PRINCIPAL
    return None


def install_auth_routes(app, settings: Settings, service: LicenseService) -> None:
    """Register /auth/* and /admin/* routes on *app*."""
    from fastapi import APIRouter, Depends, Header, HTTPException
    from pydantic import BaseModel

    router = APIRouter()

    class LoginIn(BaseModel):
        username: str
        password: str

    class TokenOut(BaseModel):
        token: str
        token_type: str = "bearer"
        expires_in: int

    class MeOut(BaseModel):
        username: str
        telegram_verified: bool

    class PairingOut(BaseModel):
        code: str
        expires_in: int

    def _bearer(authorization: str | None, x_api_key: str | None) -> str | None:
        if authorization and authorization.startswith("Bearer "):
            return authorization[len("Bearer "):]
        return x_api_key

    async def current_account(
        authorization: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None),
    ):
        token = _bearer(authorization, x_api_key)
        account = service.validate_token(token) if token else None
        if account is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token.")
        return account

    def _require_admin(x_admin_key: str | None = Header(default=None)) -> None:
        if not settings.auth_admin_key or not x_admin_key or not hmac.compare_digest(
            x_admin_key, settings.auth_admin_key
        ):
            raise HTTPException(status_code=403, detail="Admin key required.")

    # -- user-facing ----------------------------------------------------------

    @router.post("/auth/login", response_model=TokenOut)
    async def login(body: LoginIn) -> TokenOut:
        try:
            account = service.authenticate(body.username, body.password)
        except AuthError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        if settings.auth_require_telegram and not account.telegram_verified:
            raise HTTPException(
                status_code=403,
                detail="Link your Telegram account before signing in.",
            )
        token = service.issue_token(account.id)
        return TokenOut(token=token, expires_in=settings.auth_token_ttl_hours * 3600)

    @router.get("/auth/me", response_model=MeOut)
    async def me(account=Depends(current_account)) -> MeOut:
        return MeOut(username=account.username,
                    telegram_verified=account.telegram_verified)

    @router.post("/auth/pairing-code", response_model=PairingOut)
    async def pairing_code(account=Depends(current_account)) -> PairingOut:
        code = service.create_pairing_code(account.id)
        return PairingOut(code=code, expires_in=600)

    @router.post("/auth/logout")
    async def logout(
        authorization: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None),
    ) -> dict:
        token = _bearer(authorization, x_api_key)
        if token:
            service.revoke_token(token)
        return {"status": "logged_out"}

    # -- admin (operator) -----------------------------------------------------

    class CreateAccountIn(BaseModel):
        username: str
        password: str

    class IssueLicenseIn(BaseModel):
        username: str
        plan: str = "standard"
        valid_days: int | None = None

    @router.post("/admin/accounts")
    async def admin_create_account(
        body: CreateAccountIn, _: None = Depends(_require_admin)
    ) -> dict:
        try:
            account = service.create_account(body.username, body.password)
        except AuthError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"username": account.username, "id": account.id}

    @router.post("/admin/licenses")
    async def admin_issue_license(
        body: IssueLicenseIn, _: None = Depends(_require_admin)
    ) -> dict:
        account = service.get_account(body.username)
        if account is None:
            raise HTTPException(status_code=404, detail="Account not found.")
        key = service.issue_license(
            account.id, plan=body.plan, valid_days=body.valid_days
        )
        # The plaintext key is returned exactly once — it is stored only hashed.
        return {"username": account.username, "license_key": key, "plan": body.plan}

    app.include_router(router)
