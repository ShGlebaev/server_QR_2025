import os
import qrcode
import random
import string
import re

os.makedirs("QRFolder", exist_ok=True)

def generate_random_string(length=12):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def create_qr_code_with_key():
    random_string = generate_random_string()
    sanitized_string = sanitize_filename(random_string)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(random_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    file_path = f"QRFolder/{sanitized_string}.png"
    img.save(file_path)
    return file_path, sanitized_string
