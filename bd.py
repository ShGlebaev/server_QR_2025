import sqlite3
import bcrypt

class Database:
    def __init__(self, db_name="users.db"):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                qr_code TEXT,
                life_time INTEGER
            )
        ''')
        self.connection.commit()

    def register_user(self, login: str, password: str) -> bool:
        try:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            self.cursor.execute("SELECT * FROM users WHERE login = ?", (login,))
            if self.cursor.fetchone() is not None:
                print(f"Пользователь с логином {login} уже существует")
                return False
            else:
                self.cursor.execute("INSERT INTO users (login, password) VALUES (?, ?)", (login, hashed_password))
                self.connection.commit()
                print(f"Пользователь {login} успешно зарегистрирован")
                return True
        except Exception as e:
            print(f"Ошибка при регистрации: {e}")
            return False

    def authenticate_user(self, login: str, password: str):
        self.cursor.execute("SELECT password FROM users WHERE login = ?", (login,))
        stored_password = self.cursor.fetchone()
        
        if stored_password and bcrypt.checkpw(password.encode('utf-8'), stored_password[0]):
            return login
        return None

    def close(self):
        self.connection.close()
