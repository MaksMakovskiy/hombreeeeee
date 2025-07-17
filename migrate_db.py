#!/usr/bin/env python3
"""
Скрипт для миграции базы данных
Добавляет недостающие таблицы и колонки
"""

from flask_app import app
from crud import db
import sqlite3
import os

def migrate_database():
    with app.app_context():
        db_path = os.path.join(app.instance_path, 'site.db')
        
        # Создаем соединение с базой данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            print("Начинаем миграцию базы данных...")
            
            # 1. Добавляем колонку editors_allowed в таблицу classes
            try:
                cursor.execute("ALTER TABLE classes ADD COLUMN editors_allowed TEXT DEFAULT '[]'")
                print("✓ Добавлена колонка editors_allowed в таблицу classes")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print("• Колонка editors_allowed уже существует в таблице classes")
                else:
                    print(f"• Ошибка при добавлении editors_allowed в classes: {e}")
            
            # 2. Добавляем колонку editors_allowed в таблицу subclass
            try:
                cursor.execute("ALTER TABLE subclass ADD COLUMN editors_allowed TEXT DEFAULT '[]'")
                print("✓ Добавлена колонка editors_allowed в таблицу subclass")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print("• Колонка editors_allowed уже существует в таблице subclass")
                else:
                    print(f"• Ошибка при добавлении editors_allowed в subclass: {e}")
            
            # 3. Создаем таблицу races если её нет
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS races (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(100) NOT NULL,
                        description TEXT NOT NULL,
                        image_url VARCHAR(255),
                        user_id INTEGER NOT NULL,
                        editors_allowed TEXT DEFAULT '[]',
                        FOREIGN KEY (user_id) REFERENCES user (id)
                    )
                """)
                print("✓ Создана таблица races")
            except sqlite3.OperationalError as e:
                print(f"• Ошибка при создании таблицы races: {e}")
            
            # 4. Создаем таблицу food если её нет
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS food (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(100) NOT NULL,
                        description TEXT NOT NULL,
                        user_id INTEGER NOT NULL,
                        editors_allowed TEXT DEFAULT '[]',
                        FOREIGN KEY (user_id) REFERENCES user (id)
                    )
                """)
                print("✓ Создана таблица food")
            except sqlite3.OperationalError as e:
                print(f"• Ошибка при создании таблицы food: {e}")
            
            # 5. Обновляем все существующие записи, у которых editors_allowed NULL
            try:
                cursor.execute("UPDATE classes SET editors_allowed = '[]' WHERE editors_allowed IS NULL")
                cursor.execute("UPDATE subclass SET editors_allowed = '[]' WHERE editors_allowed IS NULL")
                cursor.execute("UPDATE races SET editors_allowed = '[]' WHERE editors_allowed IS NULL")
                cursor.execute("UPDATE food SET editors_allowed = '[]' WHERE editors_allowed IS NULL")
                print("✓ Обновлены значения editors_allowed")
            except sqlite3.OperationalError as e:
                print(f"• Ошибка при обновлении значений: {e}")
            
            # Сохраняем изменения
            conn.commit()
            print("✓ Миграция завершена успешно!")
            
        except Exception as e:
            print(f"❌ Ошибка миграции: {e}")
            conn.rollback()
        finally:
            conn.close()

if __name__ == "__main__":
    migrate_database()
