# crud.py

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    
    # Relationships
    comments = db.relationship('Comment', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    classes = db.relationship('Class', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    subclasses = db.relationship('Subclass', backref='author', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Class(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    hit_dice = db.Column(db.String(10), nullable=False)
    hit_points_first = db.Column(db.String(100), nullable=False)
    hit_points_next = db.Column(db.String(100), nullable=False)
    armor_proficiencies = db.Column(db.Text, nullable=False)
    weapon_proficiencies = db.Column(db.Text, nullable=False)
    tool_proficiencies = db.Column(db.Text, nullable=False)
    saving_throws = db.Column(db.String(100), nullable=False)
    skills = db.Column(db.Text, nullable=False)
    custom_columns_json = db.Column(db.Text, default='[]')  # Только тут!
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    editors_allowed = db.Column(db.JSON, default=list)  # список user_id

    # Relationships
    abilities = db.relationship('Ability', backref='class_ref', lazy='dynamic', 
                              primaryjoin="and_(Class.id==Ability.class_id, Ability.parent_id==None)",
                              cascade='all, delete-orphan')
    table_rows = db.relationship('ClassTableRow', backref='class_ref', lazy='dynamic',
                               cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='class_ref', lazy='dynamic',
                             cascade='all, delete-orphan')
    subclasses = db.relationship('Subclass', backref='parent_class', lazy='dynamic',
                               cascade='all, delete-orphan')

class Subclass(db.Model):
    __tablename__ = 'subclass'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    editors_allowed = db.Column(db.JSON, default=list)  # список user_id

    # Relationships
    abilities = db.relationship('Ability', backref='subclass_ref', lazy='dynamic',
                              cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='subclass_ref', lazy='dynamic',
                             cascade='all, delete-orphan')

class Ability(db.Model):
    __tablename__ = 'ability'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    level = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    subclass_id = db.Column(db.Integer, db.ForeignKey('subclass.id'))
    parent_id = db.Column(db.Integer, db.ForeignKey('ability.id'))
    custom_table = db.Column(db.JSON)

    # Self-referential relationship for nested abilities
    children = db.relationship('Ability', backref=db.backref('parent', remote_side=[id]),
                             cascade='all, delete-orphan')

class ClassTableRow(db.Model):
    __tablename__ = 'class_table_row'
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    level = db.Column(db.Integer, nullable=False)
    proficiency_bonus = db.Column(db.Integer, nullable=False)
    custom = db.Column(db.JSON, default={})  # Значения для кастомных колонок

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    subclass_id = db.Column(db.Integer, db.ForeignKey('subclass.id'))

class Race(db.Model):
    __tablename__ = 'races'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    editors_allowed = db.Column(db.JSON, default=list)
    abilities = db.relationship('RaceAbility', backref='race_ref', lazy='dynamic', cascade='all, delete-orphan')

class RaceAbility(db.Model):
    __tablename__ = 'race_ability'
    id = db.Column(db.Integer, primary_key=True)
    race_id = db.Column(db.Integer, db.ForeignKey('races.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)

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
    if not user_id:
        return False
    # Автор всегда может редактировать
    if hasattr(content_object, "user_id") and content_object.user_id == user_id:
        return True
    # Проверка прав редактора
    editors = getattr(content_object, "editors_allowed", [])
    return user_id in editors

def grant_edit_permission(grantor_user_id, target_user_id, content_object):
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