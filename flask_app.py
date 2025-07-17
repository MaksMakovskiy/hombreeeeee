# flask_app.py

from flask import Flask, g
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from routes import auth_bp, classes_bp, subclasses_bp, profile_bp, main_bp
from routes.races.routes import races_bp
from crud import db
from markupsafe import Markup
import os
from routes.food.routes import food_bp

app = Flask(__name__)

# Создаём instance-папку, если её нет
os.makedirs(app.instance_path, exist_ok=True)

app.config['SECRET_KEY'] = 'очень_сложный_секретный_ключ_для_проекта_dnd_2025_07_05'
db_path = os.path.join(app.instance_path, 'site.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация CSRF защиты
csrf = CSRFProtect(app)

# Регистрация blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(classes_bp)
app.register_blueprint(subclasses_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(main_bp)
app.register_blueprint(races_bp)
app.register_blueprint(food_bp)

db.init_app(app)
with app.app_context():
    db.create_all()

@app.template_filter('nl2br')
def nl2br(value):
    return Markup(value.replace('\n', '<br>'))

@app.context_processor
def inject_logout_form():
    from routes.auth.routes import LogoutForm
    return dict(logout_form=LogoutForm())

@app.context_processor
def inject_user():
    return dict(user=getattr(g, 'user', None))
