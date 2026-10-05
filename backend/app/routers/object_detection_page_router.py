from fastapi import APIRouter, Request
from app.core.templating import templates

router = APIRouter(tags=["Object Detection Page"])


@router.get("/dashboard/object-detection")
def object_detection_page(request: Request):
    return templates.TemplateResponse(
        request,
        "object_detection/index.html",
        {"request": request},
    )
