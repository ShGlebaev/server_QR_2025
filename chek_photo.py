import os
import time
import asyncio
from PIL import Image
from pyzbar.pyzbar import decode
from bd import Database
from door_lock import DoorLock
import logging

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.makedirs("shot_images", exist_ok=True)

# Настройки
IMAGE_FOLDER = "shot_images"
MAX_AGE_NO_QR = 30
DELETE_INTERVAL = 300  # 5 минут в секундах

def scan_qr_code(image_path):
    """Сканирует QR-код на изображении и возвращает текст"""
    try:
        img = Image.open(image_path)
        decoded_objects = decode(img)
        if decoded_objects:
            return decoded_objects[0].data.decode("utf-8")
        return None
    except Exception as e:
        logger.error(f"Ошибка при обработке {image_path}: {e}")
        return None

def check_key_in_db(qr_key: str) -> bool:
    """Проверяет наличие ключа в базе данных"""
    db = Database('users.db')
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE qr_code = ?", (qr_key,))
        return cursor.fetchone() is not None

def scan_and_process_image(filepath):
    """Обрабатывает одно конкретное изображение"""
    qr_text = scan_qr_code(filepath)
    
    if qr_text:
        logger.info(f"Найден QR-код в {os.path.basename(filepath)}: {qr_text}")
        
        # Проверяем ключ в базе данных
        if check_key_in_db(qr_text):
            logger.info("Ключ найден в базе данных. Открываем дверь.")
            door_lock = DoorLock()
            door_lock.open_door()
            return True
        else:
            logger.warning("Ключ не найден в базе данных. Доступ запрещен.")
            return False
    else:
        try:
            os.remove(filepath)
            logger.info(f"Удалено (нет QR-кода): {os.path.basename(filepath)}")
        except Exception as e:
            logger.error(f"Ошибка удаления {filepath}: {e}")
        return False

async def delit_image():
    """Периодически очищает папку с изображениями"""
    while True:
        try:
            await asyncio.sleep(DELETE_INTERVAL)
            files = [
                os.path.join(IMAGE_FOLDER, f) 
                for f in os.listdir(IMAGE_FOLDER) 
                if f.lower().endswith(('.png', '.jpg', '.jpeg'))
            ]
            for filepath in files:
                try:
                    os.remove(filepath)
                    logger.info(f"Удален файл: {os.path.basename(filepath)}")
                except Exception as e:
                    logger.error(f"Ошибка при удалении {filepath}: {e}")
            logger.info("Очистка папки shot_images завершена")
        except Exception as e:
            logger.error(f"Ошибка в процессе очистки папки: {e}")

async def process_image_from_endpoint(file_path: str):
    """Обрабатывает изображение, полученное через эндпоинт"""
    try:
        scan_and_process_image(file_path)
    except Exception as e:
        logger.error(f"Ошибка при обработке изображения {file_path}: {e}")

async def start_delete_task():
    """Запускает задачу очистки папки"""
    asyncio.create_task(delit_image())

if __name__ == "__main__":
    asyncio.run(delit_image())
