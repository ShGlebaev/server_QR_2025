from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
import os
import logging
from pydantic import BaseModel
from generator import create_qr_code
from bd import Database


# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserRegisterRequest(BaseModel):
    login: str
    password: str

class UserLoginRequest(BaseModel):
    login: str
    password: str

app = FastAPI()

# Конфигурация CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Предоставление статических файлов из QRfolder
os.makedirs("QRfolder", exist_ok=True)
app.mount("/QRfolder", StaticFiles(directory="QRfolder"), name="QRfolder")

# Инициализация базы данных
db = Database("users.db")

# Ручка для генерации QR-кода
@app.get("/show")
async def show_qr_kod(request: Request):
    try:
        qr_code_path = create_qr_code()  # Получаем путь к файлу с QR-кодом
        if qr_code_path and os.path.exists(qr_code_path):
            qr_code_url = f"{request.url.scheme}://{request.url.hostname}:{request.url.port}/QRfolder/{os.path.basename(qr_code_path)}"
            # Запускаем асинхронное удаление файла через 60 секунд
            asyncio.create_task(remove_qr_code_after_delay(qr_code_path))
            return {"qr_code": qr_code_url}
        else:
            raise HTTPException(status_code=500, detail="Не удалось сгенерировать QR-код")
    except Exception as e:
        logger.error(f"Ошибка при генерации QR-кода: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Ручка для регистрации пользователя
@app.post("/auth/register")
async def register_user(request: UserRegisterRequest):
    try:
        if not db.register_user(login=request.login, password=request.password):
            raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")
        return {"status": "success", "message": "Пользователь успешно зарегистрирован"}
    except Exception as e:
        logger.error(f"Ошибка при регистрации: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Ручка для авторизации пользователя
@app.post("/auth/login")
async def login_user(request: UserLoginRequest):
    try:
        user = db.authenticate_user(request.login, request.password)

        if user:
            return {"message": "Авторизация успешна", "user": {"login": user}}
        else:
            raise HTTPException(status_code=401, detail="Неверные учетные данные")
    except Exception as e:
        logger.error(f"Ошибка при авторизации: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Удаление QR-кодов через заданное время
async def remove_qr_code_after_delay(qr_code_path):
    try:
        await asyncio.sleep(60)
        if os.path.exists(qr_code_path):
            os.remove(qr_code_path)
            logger.info(f"QR-код {qr_code_path} удален.")
    except Exception as e:
        logger.error(f"Ошибка при удалении QR-кода: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)