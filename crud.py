# crud.py

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime # Для временных меток комментариев

db = SQLAlchemy()

# --- Существующая модель User ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    # Добавляем связи для удобства доступа:
    # user.classes_authored будет списком классов, созданных этим пользователем
    classes_authored = db.relationship('Class', backref='author', lazy=True, foreign_keys='Class.user_id')
    subclasses_authored = db.relationship('Subclass', backref='author', lazy=True, foreign_keys='Subclass.user_id')
    comments = db.relationship('Comment', backref='author', lazy=True)

    # Добавляем поля для разрешений на редактирование
    # Это простой подход. Для более сложной системы можно использовать отдельную таблицу разрешений.
    # users_with_edit_access = db.relationship('UserEditPermission', back_populates='editor', lazy=True, foreign_keys='UserEditPermission.editor_id')
    # edits_granted_to_me = db.relationship('UserEditPermission', back_populates='target_user', lazy=True, foreign_keys='UserEditPermission.target_user_id')


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

# --- Новые модели ---

class Class(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) # Автор класса

    subclasses = db.relationship('Subclass', backref='parent_class', lazy=True)
    abilities = db.relationship('Ability', backref='class_owner', lazy=True, cascade="all, delete-orphan", foreign_keys='Ability.class_id')
    comments = db.relationship('Comment', backref='class_comment_target', lazy=True, cascade="all, delete-orphan", foreign_keys='Comment.class_id')

    # Поле для пользователей, которым разрешено редактировать этот класс
    # Это будет список ID пользователей, сериализованный в строку
    editors_allowed_raw = db.Column(db.Text, default='[]')

    # Геттер и сеттер для работы со списком ID
    @property
    def editors_allowed(self):
        import json
        try:
            return json.loads(self.editors_allowed_raw)
        except json.JSONDecodeError:
            return []

    @editors_allowed.setter
    def editors_allowed(self, user_ids_list):
        import json
        self.editors_allowed_raw = json.dumps(user_ids_list)

    custom_columns_json = db.Column(db.Text, nullable=True)  # <-- добавьте эту строку

    hit_dice = db.Column(db.String(50))
    hit_points_first = db.Column(db.String(100))
    hit_points_next = db.Column(db.String(100))
    armor_proficiencies = db.Column(db.String(200))
    weapon_proficiencies = db.Column(db.String(200))
    tool_proficiencies = db.Column(db.String(200))
    saving_throws = db.Column(db.String(200))
    skills = db.Column(db.String(200))

    def __repr__(self):
        return f'<Class {self.name}>'

class Subclass(db.Model):
    __tablename__ = 'subclasses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) # Автор подкласса

    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False) # Привязка к родительскому классу

    abilities = db.relationship('Ability', backref='subclass_owner', lazy=True, cascade="all, delete-orphan", foreign_keys='Ability.subclass_id')
    comments = db.relationship('Comment', backref='subclass_comment_target', lazy=True, cascade="all, delete-orphan", foreign_keys='Comment.subclass_id')

    # Поле для пользователей, которым разрешено редактировать этот подкласс
    editors_allowed_raw = db.Column(db.Text, default='[]')

    @property
    def editors_allowed(self):
        import json
        try:
            return json.loads(self.editors_allowed_raw)
        except json.JSONDecodeError:
            return []

    @editors_allowed.setter
    def editors_allowed(self, user_ids_list):
        import json
        self.editors_allowed_raw = json.dumps(user_ids_list)

    def __repr__(self):
        return f'<Subclass {self.name}>'

class Ability(db.Model):
    __tablename__ = 'abilities'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    level = db.Column(db.Integer, nullable=False) # Уровень разблокировки
    type = db.Column(db.String(50)) # Например, 'active', 'passive', 'feature'
    parent_id = db.Column(db.Integer, db.ForeignKey('abilities.id'), nullable=True) # Для вложенных способностей

    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=True) # Привязка к классу (если это классовая способность)
    subclass_id = db.Column(db.Integer, db.ForeignKey('subclasses.id'), nullable=True) # Привязка к подклассу (если это подклассовая способность)

    # Вложенные способности
    children = db.relationship('Ability', backref=db.backref('parent', remote_side=[id]), lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Ability {self.name} (Lvl {self.level})>'

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) # Автор комментария

    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=True) # Привязка к классу
    subclass_id = db.Column(db.Integer, db.ForeignKey('subclasses.id'), nullable=True) # Привязка к подклассу

    # Проверка, что комментарий привязан либо к классу, либо к подклассу
    __table_args__ = (
        db.CheckConstraint('(class_id IS NOT NULL AND subclass_id IS NULL) OR (class_id IS NULL AND subclass_id IS NOT NULL)',
                           name='chk_class_or_subclass_id'),
    )

    def __repr__(self):
        return f'<Comment {self.id} by {self.user_id}>'

class ClassTableRow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    level = db.Column(db.Integer, nullable=False)
    proficiency_bonus = db.Column(db.Integer, nullable=False)
    custom = db.Column(db.JSON, nullable=True)  # Пользовательские поля

    __table_args__ = (db.UniqueConstraint('class_id', 'level', name='_class_level_uc'),)

# --- Вспомогательные функции для пользователей (существующие) ---
def create_user(username, password):
    if User.query.filter_by(username=username).first():
        return None  # Пользователь уже существует
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, password_hash=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return new_user

def get_user_by_username(username):
    return User.query.filter_by(username=username).first()

def get_user_by_id(user_id):
    return User.query.get(user_id)

def update_user_password(user_id, new_password):
    user = User.query.get(user_id)
    if user:
        user.set_password(new_password)
        db.session.commit()
        return True
    return False

def delete_user(user_id):
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        return True
    return False

# --- Вспомогательные функции для классов, подклассов, комментариев и прав (новые) ---

def get_all_classes():
    return Class.query.all()

def get_all_subclasses():
    return Subclass.query.all()

def add_comment(user_id, text, class_id=None, subclass_id=None):
    if not class_id and not subclass_id:
        return None # Комментарий должен быть привязан к чему-то
    comment = Comment(user_id=user_id, text=text, class_id=class_id, subclass_id=subclass_id)
    db.session.add(comment)
    db.session.commit()
    return comment

def is_allowed_to_edit(user_id, content_object):
    """Проверяет, имеет ли пользователь права на редактирование объекта."""
    if not user_id:
        return False
    # Если пользователь - автор
    if content_object.user_id == user_id:
        return True
    # Если пользователь в списке разрешенных редакторов
    if user_id in content_object.editors_allowed:
        return True
    return False

def grant_edit_permission(target_user_id, content_object, grantor_user_id):
    """
    Выдает права на редактирование объекта другому пользователю.
    Только автор объекта может выдавать права.
    """
    if not is_allowed_to_edit(grantor_user_id, content_object) and content_object.user_id != grantor_user_id:
        return False, "Только автор или текущий редактор может выдавать права."

    # Убедимся, что target_user_id существует
    if not get_user_by_id(target_user_id):
        return False, "Целевой пользователь не найден."

    allowed_editors = content_object.editors_allowed
    if target_user_id not in allowed_editors:
        allowed_editors.append(target_user_id)
        content_object.editors_allowed = allowed_editors # Используем сеттер property
        db.session.commit()
        return True, "Права успешно выданы."
    return False, "У пользователя уже есть права на редактирование."