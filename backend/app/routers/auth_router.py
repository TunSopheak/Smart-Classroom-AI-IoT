from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.auth import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    create_session_cookie,
    get_current_user_from_request,
    verify_demo_user,
)

router = APIRouter(tags=["Authentication"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login")
def login_page(request: Request, next: str = "/dashboard"):
    current_user = get_current_user_from_request(request)

    if current_user:
        return RedirectResponse(url=next or "/dashboard", status_code=303)

    return templates.TemplateResponse(
        request,
        "auth/login.html",
        {
            "request": request,
            "next": next,
            "error": request.query_params.get("error"),
        },
    )


@router.post("/login")
def login_submit(
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/dashboard"),
):
    user = verify_demo_user(username=username.strip(), password=password.strip())

    if not user:
        return RedirectResponse(
            url=f"/login?error=Invalid username or password&next={next}",
            status_code=303,
        )

    response = RedirectResponse(url=next or "/dashboard", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_cookie(user),
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
    )

    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@router.post("/logout")
def logout_post():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@router.get("/api/auth/me")
def auth_me(request: Request):
    user = get_current_user_from_request(request)

    if not user:
        return JSONResponse(
            status_code=401,
            content={
                "authenticated": False,
                "user": None,
            },
        )

    return {
        "authenticated": True,
        "user": user,
    }
