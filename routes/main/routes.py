from flask import Blueprint, render_template, redirect, url_for, g
from crud import db, Class, Subclass

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def index():
    return render_template("main.html.jinja", user=g.user)

@main_bp.route("/dashboard")
def dashboard():
    if not g.user:
        return redirect(url_for('auth.login'))
    user_classes = Class.query.filter_by(user_id=g.user.id).all()
    user_subclasses = Subclass.query.filter_by(user_id=g.user.id).all()
    return render_template('dashboard.html.jinja',
                         user=g.user,
                         user_classes=user_classes,
                         user_subclasses=user_subclasses)
