import os
import time
import asyncio
from PIL import Image
from pyzbar.pyzbar import decode
from bd import Database
from door_lock import DoorLock

os.makedirs("shot_images", exist_ok=True)

# Настройки
IMAGE_FOLDER = "shot_images"
MAX_AGE_NO_QR = 30

def scan_qr_code(image_path):
    """Сканирует QR-код на изображении и возвращает текст"""
    try:
        img = Image.open(image_path)
        decoded_objects = decode(img)
        if decoded_objects:
            return decoded_objects[0].data.decode("utf-8")
        return None
    except Exception as e:
        print(f"Ошибка при обработке {image_path}: {e}")
        return None

def check_key_in_db(qr_key: str) -> bool:
    """Проверяет наличие ключа в базе данных"""
    db = Database('users.db')
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE key = ?", (qr_key,))
        return cursor.fetchone() is not None

def scan_and_process_image(filepath):
    """Обрабатывает одно конкретное изображение"""
    qr_text = scan_qr_code(filepath)
    
    if qr_text:
        print(f"Найден QR-код в {os.path.basename(filepath)}: {qr_text}")
        
        # Проверяем ключ в базе данных
        if check_key_in_db(qr_text):
            print("Ключ найден в базе данных. Открываем дверь.")
            door_lock = DoorLock()
            door_lock.open_door()
            return True
        else:
            print("Ключ не найден в базе данных. Доступ запрещен.")
            return False
    else:
        try:
            os.remove(filepath)
            print(f"Удалено (нет QR-кода): {os.path.basename(filepath)}")
        except Exception as e:
            print(f"Ошибка удаления {filepath}: {e}")
        return False

async def monitor_folder():
    print(f"Мониторинг папки {IMAGE_FOLDER}...")
    while True:
        files = [
            os.path.join(IMAGE_FOLDER, f) 
            for f in os.listdir(IMAGE_FOLDER) 
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]
        for filepath in files:
            file_age = time.time() - os.path.getmtime(filepath)
            if file_age > MAX_AGE_NO_QR:
                scan_and_process_image(filepath)
        await asyncio.sleep(10)

async def delit_image():
    while True:
        try:
            await asyncio.sleep(300)
            files = [
                os.path.join(IMAGE_FOLDER, f) 
                for f in os.listdir(IMAGE_FOLDER) 
                if f.lower().endswith(('.png', '.jpg', '.jpeg'))
            ]
            for filepath in files:
                try:
                    os.remove(filepath)
                    print(f"Удален файл: {os.path.basename(filepath)}")
                except Exception as e:
                    print(f"Ошибка при удалении {filepath}: {e}")
            print("Очистка папки shot_images завершена")
        except Exception as e:
            print(f"Ошибка в процессе очистки папки: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(monitor_folder())