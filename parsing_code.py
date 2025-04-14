import json
from bd import Database  # Импорт вашего класса Database

def json_to_sqlite(json_path: str, db: Database):
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    for entry in data:
        db.import_user_data(
            lastname=entry['lastname'],
            initials=entry['initials']
        )

# Использование
if __name__ == "__main__":
    db = Database('my_database.db')
    json_to_sqlite('input.json', db)
