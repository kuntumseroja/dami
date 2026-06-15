"""AuthN/AuthZ skeleton.

Two modes:
- ``dev``  — identity from ``X-User-Id`` / ``X-User-Roles`` headers; if absent
  in a development environment, a default admin user is assumed so local
  exploration stays frictionless.
- ``oidc`` — integration point for enterprise SSO. Bearer-token validation is
  Sprint-1-scoped to the seam only; wire the IdP here (issuer, JWKS, audience)
  without touching any inner layer.

Sign-off identity always comes from the authenticated user, never from
request bodies — this is the liability requirement.
"""
from fastapi import Depends, HTTPException, Request

from app.domain.models import DEFAULT_ENTITY, BPIEntity, Role, User
from app.infrastructure.config import get_settings

DEV_ADMIN = User(id="dev-admin", name="Development Admin", roles=[Role.ADMIN],
                 entity=DEFAULT_ENTITY)


def get_current_user(request: Request) -> User:
    settings = get_settings()

    if settings.auth_mode == "oidc":
        # OIDC seam: validate Authorization: Bearer <jwt> against the IdP.
        raise HTTPException(501, "OIDC validation not configured yet")

    user_id = request.headers.get("X-User-Id")
    roles_header = request.headers.get("X-User-Roles", "")
    entity_header = request.headers.get("X-User-Entity", DEFAULT_ENTITY.value)
    if user_id:
        roles = []
        for raw in roles_header.split(","):
            raw = raw.strip()
            if not raw:
                continue
            try:
                roles.append(Role(raw))
            except ValueError as exc:
                raise HTTPException(400, f"unknown role '{raw}'") from exc
        try:
            entity = BPIEntity(entity_header)
        except ValueError as exc:
            raise HTTPException(400, f"unknown entity '{entity_header}'") from exc
        return User(id=user_id, name=user_id, roles=roles, entity=entity)

    if settings.dam_env == "development":
        return DEV_ADMIN
    raise HTTPException(401, "authentication required")


def require_roles(*roles: Role):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if not user.has_role(*roles):
            raise HTTPException(
                403, f"requires one of roles: {', '.join(r.value for r in roles)}"
            )
        return user

    return dependency
