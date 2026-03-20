from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
import uuid, os, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

app = FastAPI()

UPLOAD_DIR = "uploads"
SECRET_KEY = "change-me-in-production"
ALGORITHM = "HS256"
ALLOWED_TYPES = {"image/jpeg", "image/png"}
MAX_SIZE = 5 * 1024 * 1024
os.makedirs(UPLOAD_DIR, exist_ok=True)

photos_db: list[dict] = []
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2 = OAuth2PasswordBearer(tokenUrl="login")
users_db = {"john": pwd.hash("secret123")}  # username: hashed_password

def make_token(username: str) -> str:
    return jwt.encode(
        {"sub": username, "exp": datetime.utcnow() + timedelta(minutes=30)},
        SECRET_KEY, algorithm=ALGORITHM
    )

def current_user(token: str = Depends(oauth2)) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Невалідний токен")

class UserCreate(BaseModel):
    username: str
    password: str

@app.post("/register", status_code=201)
def register(user: UserCreate):
    if user.username in users_db:
        raise HTTPException(400, "Користувач вже існує")
    users_db[user.username] = pwd.hash(user.password)
    return {"message": "Зареєстровано"}

@app.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    hashed = users_db.get(form.username)
    if not hashed or not pwd.verify(form.password, hashed):
        raise HTTPException(401, "Невірний логін або пароль")
    return {"access_token": make_token(form.username), "token_type": "bearer"}

@app.post("/photos/upload")
async def upload(file: UploadFile = File(...), user: str = Depends(current_user)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Тільки JPEG та PNG")
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, "Максимум 5MB")
    ext = "jpg" if file.content_type == "image/jpeg" else "png"
    name = f"{uuid.uuid4()}.{ext}"
    open(os.path.join(UPLOAD_DIR, name), "wb").write(content)
    photo = {"filename": name, "url": f"/photos/{name}", "uploaded_by": user,
             "uploaded_at": datetime.utcnow().isoformat(), "size": len(content)}
    photos_db.append(photo)
    return photo

@app.get("/photos/list")
def list_photos(user: str = Depends(current_user)):
    return sorted(photos_db, key=lambda x: x["uploaded_at"], reverse=True)

@app.get("/photos/{filename}")
def get_photo(filename: str, user: str = Depends(current_user)):
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(404, "Фото не знайдено")
    return FileResponse(path)