# flask_app.py

from flask import Flask, g
from flask_sqlalchemy import SQLAlchemy
from routes import auth_bp, classes_bp, subclasses_bp, profile_bp, main_bp
from crud import db
from markupsafe import Markup

app = Flask(__name__)

app.config['SECRET_KEY'] = 'очень_сложный_секретный_ключ_для_проекта_dnd_2025_07_05'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Регистрация blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(classes_bp)
app.register_blueprint(subclasses_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(main_bp)

db.init_app(app)
with app.app_context():
    db.create_all()

@app.template_filter('nl2br')
def nl2br(value):
    return Markup(value.replace('\n', '<br>'))

@app.context_processor
def inject_user():
    return dict(user=getattr(g, 'user', None))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8989)