from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from app.core.templating import templates

from app.core.auth import (
    get_current_user_from_request,
    get_device_user_from_request,
    is_protected_path,
    is_public_path,
    user_can_access_path,
)




async def auth_middleware(request: Request, call_next):
    """Require a logged-in user (or a trusted device key) for protected paths."""
    path = request.url.path

    current_user = get_current_user_from_request(request) or get_device_user_from_request(request)
    request.state.current_user = current_user

    if is_public_path(path) or not is_protected_path(path):
        return await call_next(request)

    if not current_user:
        if path.startswith("/api"):
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Authentication required."},
            )
        return RedirectResponse(url=f"/login?next={path}", status_code=303)

    if not user_can_access_path(current_user, path):
        if path.startswith("/api"):
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "message": "You do not have permission to access this resource.",
                },
            )
        return templates.TemplateResponse(
            request,
            "auth/access_denied.html",
            {"request": request, "role": current_user.get("role")},
            status_code=403,
        )

    return await call_next(request)
