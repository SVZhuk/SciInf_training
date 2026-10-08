"""Homepage: a read-only HTML view over the existing samples list query."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import RepoDep
from app.schemas import Organism, SampleRead

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def homepage(request: Request, repo: RepoDep) -> HTMLResponse:
    items, total = await repo.list(organism=None, limit=50, offset=0)
    samples = [SampleRead.model_validate(s) for s in reversed(items)]
    context = {"samples": samples, "total": total, "organisms": list(Organism)}
    return templates.TemplateResponse(request, "index.html", context)
