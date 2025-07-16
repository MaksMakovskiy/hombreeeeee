from routes.auth.routes import auth_bp
from routes.classes.routes import classes_bp
from routes.subclasses.routes import subclasses_bp
from routes.profile.routes import profile_bp
from routes.main.routes import main_bp

__all__ = ['auth_bp', 'classes_bp', 'subclasses_bp', 'profile_bp', 'main_bp']
