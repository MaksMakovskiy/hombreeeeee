#!/usr/bin/env python3
"""
Скрипт для добавления поддержки статей в базу данных
Добавляет таблицу articles и обновляет comments
"""

from flask_app import app
from crud import db
import sqlite3
import os

def migrate_articles():
    with app.app_context():
        db_path = os.path.join(app.instance_path, 'site.db')
        
        # Создаем соединение с базой данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            print("Начинаем миграцию для статей...")
            
            # 1. Создаем таблицу articles
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS articles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title VARCHAR(200) NOT NULL,
                        content TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        user_id INTEGER NOT NULL,
                        editors_allowed TEXT DEFAULT '[]',
                        FOREIGN KEY (user_id) REFERENCES user (id)
                    )
                """)
                print("✓ Создана таблица articles")
            except sqlite3.OperationalError as e:
                print(f"• Ошибка при создании таблицы articles: {e}")
            
            # 2. Добавляем колонку article_id в таблицу comments
            try:
                cursor.execute("ALTER TABLE comments ADD COLUMN article_id INTEGER")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_article_id ON comments(article_id)")
                print("✓ Добавлена колонка article_id в таблицу comments")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print("• Колонка article_id уже существует в таблице comments")
                else:
                    print(f"• Ошибка при добавлении article_id в comments: {e}")
            
            # Сохраняем изменения
            conn.commit()
            print("✓ Миграция статей завершена успешно!")
            
        except Exception as e:
            print(f"❌ Ошибка миграции: {e}")
            conn.rollback()
        finally:
            conn.close()

if __name__ == "__main__":
    migrate_articles()
