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

    batch = models.UploadBatch(filename=file.filename, row_count=0)
    db.add(batch)
    db.flush()  # assigns batch.id without committing yet

    inserted = 0
    for execution in executions:
        # ON CONFLICT DO NOTHING skips the whole row (batch_id included) when
        # external_id already exists, so a duplicate fill keeps belonging to
        # whichever batch first inserted it rather than being reattributed
        # to this upload.
        stmt = (
            insert(models.Execution)
            .values(**execution, batch_id=batch.id)
            .on_conflict_do_nothing(index_elements=["external_id"])
        )
        result = db.execute(stmt)
        inserted += result.rowcount or 0

    batch.row_count = inserted
    db.commit()

    return schemas.UploadResult(
        parsed=len(executions),
        inserted=inserted,
        skipped_duplicates=len(executions) - inserted,
    )


@router.get("/uploads", response_model=list[schemas.UploadBatchOut])
def list_uploads(db: Session = Depends(database.get_db)):
    batches = db.query(models.UploadBatch).order_by(models.UploadBatch.uploaded_at.desc()).all()
    return batches


@router.delete("/uploads/{batch_id}")
def delete_upload(batch_id: int, db: Session = Depends(database.get_db)):
    batch = db.query(models.UploadBatch).filter(models.UploadBatch.id == batch_id).first()
    if batch is None:
        raise HTTPException(status_code=404, detail="Upload batch not found")

    deleted = (
        db.query(models.Execution).filter(models.Execution.batch_id == batch_id).delete()
    )
    db.delete(batch)
    db.commit()

    return {"deleted_fills": deleted}
