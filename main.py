from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from datetime import datetime
import uuid
import os
import shutil

app = FastAPI(title="Photo Gallery")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

photos_db: list[dict] = []

ALLOWED_TYPES = {"image/jpeg", "image/png"}
MAX_SIZE = 5 * 1024 * 1024


@app.post("/photos/upload")
async def upload_photo(file: UploadFile = File(...)):

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Дозволені тільки JPEG та PNG файли"
        )

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Файл перевищує максимальний розмір 5MB"
        )

    extension = "jpg" if file.content_type == "image/jpeg" else "png"
    unique_filename = f"{uuid.uuid4()}.{extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as f:
        f.write(content)

    photo_info = {
        "filename": unique_filename,
        "original_name": file.filename,
        "url": f"/photos/{unique_filename}",
        "uploaded_at": datetime.utcnow().isoformat(),
        "size": len(content),
    }
    photos_db.append(photo_info)

    return {
        "message": "Фото успішно завантажено",
        "photo": photo_info
    }


@app.get("/photos/list")
async def list_photos():
    sorted_photos = sorted(
        photos_db,
        key=lambda x: x["uploaded_at"],
        reverse=True
    )
    return {
        "total": len(sorted_photos),
        "photos": sorted_photos
    }



@app.get("/photos/{filename}")
async def get_photo(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Фото не знайдено")

    return FileResponse(file_path)