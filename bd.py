import sqlite3
import bcrypt

class Database:
    def __init__(self, db_name="users.db"):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.create_table()

    def _get_connection(self):
        return self.connection

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
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            self.cursor.execute("INSERT INTO users (login, password, qr_code, life_time) VALUES (?, ?, NULL, NULL)", (login, hashed_password))
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def authenticate_user(self, login: str, password: str):
        self.cursor.execute("SELECT password FROM users WHERE login = ?", (login,))
        stored_password = self.cursor.fetchone()
        if stored_password and bcrypt.checkpw(password.encode('utf-8'), stored_password[0].encode('utf-8')):
            return login
        return None

    def close(self):
        self.connection.close()
