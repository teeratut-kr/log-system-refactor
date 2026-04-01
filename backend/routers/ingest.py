from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import ValidationError

from ..api_models import FileIngestResponse, IngestSingleResponse
from ..normalizer import normalize_log, normalize_source
from ..parsers import parse_uploaded_file
from ..schemas import SingleIngestRequest

router = APIRouter()


@router.post("/ingest", response_model=IngestSingleResponse)
async def ingest_single(request: Request, payload: SingleIngestRequest):
    try:
        original_payload = await request.json()
        item = payload.model_dump(by_alias=True, exclude_none=False)

        normalized = normalize_log(
            item,
            default_source=payload.source.value if payload.source else "api",
            original_raw=original_payload,
        )
        await request.app.state.storage.save_log(normalized)
        return {
            "status": "ok",
            "message": "log ingested and normalized successfully",
            "data": normalized,
            "auth": None,
        }
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/ingest/file", response_model=FileIngestResponse)
async def ingest_file(
    request: Request,
    file: UploadFile = File(...),
    tenant: Optional[str] = Form(default=None),
    source_hint: str = Form(default="network"),
):
    source_hint = normalize_source(source_hint, "network")
    content = await file.read()

    try:
        items = parse_uploaded_file(
            filename=file.filename or "upload.bin",
            content=content,
            tenant=tenant,
            source_hint=source_hint,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    accepted = []
    errors = []

    for index, item in enumerate(items):
        try:
            normalized = normalize_log(item, default_source=source_hint)
            await request.app.state.storage.save_log(normalized)
            accepted.append(normalized)
        except ValidationError as exc:
            errors.append({"index": index, "detail": exc.errors(), "input": item})
        except Exception as exc:
            errors.append({"index": index, "detail": str(exc), "input": item})

    return {
        "status": "ok" if not errors else "partial_success",
        "filename": file.filename,
        "received": len(items),
        "accepted": len(accepted),
        "rejected": len(errors),
        "items": accepted,
        "errors": errors,
        "auth": None,
    }
