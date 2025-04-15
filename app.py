from fastapi import FastAPI, Request, HTTPException, Depends, status, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import asyncio
import os
import logging
import uuid
from datetime import datetime, timedelta
from jose import JWTError, jwt
from pydantic import BaseModel

from generator import create_qr_code_with_key  # Обновлённая функция генерации QR-кода
from bd import Database

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Конфигурация JWT ---
SECRET_KEY = "your_secret_key_here_change_it"  # Замените на свой секретный ключ
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# --- Инициализация FastAPI ---
app = FastAPI()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене лучше ограничить список доменов
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Статические файлы ---
os.makedirs("QRfolder", exist_ok=True)
app.mount("/QRfolder", StaticFiles(directory="QRfolder"), name="QRfolder")

# --- Инициализация базы данных ---
db = Database("users.db")

# --- OAuth2 схема ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Pydantic модели ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    login: str | None = None

class User(BaseModel):
    login: str

class UserInDB(User):
    hashed_password: bytes

# --- Вспомогательные функции для аутентификации ---

def verify_password(plain_password: str, hashed_password: bytes) -> bool:
    import bcrypt
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)

def get_user(login: str):
    # Получаем пользователя из БД
    db.cursor.execute("SELECT login, password FROM users WHERE login = ?", (login,))
    row = db.cursor.fetchone()
    if row:
        return UserInDB(login=row[0], hashed_password=row[1])
    return None

def authenticate_user(login: str, password: str):
    user = get_user(login)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Неверный токен авторизации",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        login: str = payload.get("sub")
        if login is None:
            raise credentials_exception
        token_data = TokenData(login=login)
    except JWTError:
        raise credentials_exception
    user = get_user(login=token_data.login)
    if user is None:
        raise credentials_exception
    return user

# --- Эндпоинт для получения токена ---
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Неверный логин или пароль")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.login}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- Ручка для генерации QR-кода (защищённая) ---
@app.get("/show")
async def show_qr_kod(request: Request, current_user: UserInDB = Depends(get_current_user)):
    try:
        qr_code_path, qr_key = create_qr_code_with_key()
        if qr_code_path and os.path.exists(qr_code_path):
            qr_code_url = f"{request.url.scheme}://{request.url.hostname}:{request.url.port}/QRfolder/{os.path.basename(qr_code_path)}"
            life_time = 60

            # Записываем qr_code и life_time для текущего пользователя
            try:
                db.cursor.execute(
                    "UPDATE users SET qr_code = ?, life_time = ? WHERE login = ?",
                    (qr_key, life_time, current_user.login)
                )
                db.connection.commit()
                logger.info(f"Ключ {qr_key} записан для пользователя {current_user.login}")
            except Exception as e:
                logger.error(f"Ошибка при обновлении данных пользователя: {e}")
                raise HTTPException(status_code=500, detail="Ошибка при обновлении данных пользователя")

            asyncio.create_task(remove_qr_code_after_delay(qr_code_path))
            return {"qr_code": qr_code_url}
        else:
            raise HTTPException(status_code=500, detail="Не удалось сгенерировать QR-код")
    except Exception as e:
        logger.error(f"Ошибка при генерации QR-кода: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Удаление QR-кодов через заданное время ---
async def remove_qr_code_after_delay(qr_code_path):
    try:
        await asyncio.sleep(60)
        if os.path.exists(qr_code_path):
            os.remove(qr_code_path)
            logger.info(f"QR-код {qr_code_path} удален.")
    except Exception as e:
        logger.error(f"Ошибка при удалении QR-кода: {e}")

# --- Ручки регистрации и логина (без изменений) ---
class UserRegisterRequest(BaseModel):
    login: str
    password: str

@app.post("/auth/register")
async def register_user(request: UserRegisterRequest):
    import bcrypt
    try:
        hashed_password = bcrypt.hashpw(request.password.encode('utf-8'), bcrypt.gensalt())
        db.cursor.execute("SELECT * FROM users WHERE login = ?", (request.login,))
        if db.cursor.fetchone() is not None:
            raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")
        db.cursor.execute("INSERT INTO users (login, password) VALUES (?, ?)", (request.login, hashed_password))
        db.connection.commit()
        return {"status": "success", "message": "Пользователь успешно зарегистрирован"}
    except Exception as e:
        logger.error(f"Ошибка при регистрации: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/login")
async def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Неверные учетные данные")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.login}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/take_image-bytes")
async def take_image_bytes(bytes_data: bytes = Body(..., media_type="application/octet-stream")):
    try:
        os.makedirs("shot_images", exist_ok=True)
        import uuid
        filename = f"{uuid.uuid4().hex}.png"
        file_path = os.path.join("shot_images", filename)
        with open(file_path, "wb") as f:
            f.write(bytes_data)
        return {"status": "success", "message": "Изображение успешно сохранено", "file_path": file_path}
    except Exception as e:
        logger.error(f"Ошибка при сохранении изображения: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при сохранении изображения: {str(e)}")

# --- Запуск сервера ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
