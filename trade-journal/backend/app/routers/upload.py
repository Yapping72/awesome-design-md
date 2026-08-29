from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .. import database, models, schemas
from ..parsers.ibkr import IBKRParseError, parse_ibkr_activity_csv

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload", response_model=schemas.UploadResult)
async def upload_report(
    file: UploadFile = File(...), db: Session = Depends(database.get_db)
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV IBKR Activity Statement exports are supported",
        )

    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    try:
        executions = parse_ibkr_activity_csv(text)
    except IBKRParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not executions:
        raise HTTPException(
            status_code=400,
            detail=(
                "No trade rows found. Export an IBKR Activity Statement as CSV "
                "with the 'Trades' section included."
            ),
        )

    inserted = 0
    for execution in executions:
        stmt = (
            insert(models.Execution)
            .values(**execution)
            .on_conflict_do_nothing(index_elements=["external_id"])
        )
        result = db.execute(stmt)
        inserted += result.rowcount or 0

    db.commit()

    return schemas.UploadResult(
        parsed=len(executions),
        inserted=inserted,
        skipped_duplicates=len(executions) - inserted,
    )
