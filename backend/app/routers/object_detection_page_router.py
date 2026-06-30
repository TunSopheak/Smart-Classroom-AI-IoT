from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["Object Detection Page"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard/object-detection")
def object_detection_page(request: Request):
    return templates.TemplateResponse(
        request,
        "object_detection/index.html",
        {"request": request},
    )
