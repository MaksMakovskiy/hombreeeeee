from flask import Blueprint, render_template, redirect, url_for, g, request, flash, session
from crud import db, Class, Subclass, User, Race, Food, Article
from utils.decorators import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import json

main_bp = Blueprint('main', __name__)

class GrantEditForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    submit = SubmitField('Выдать права')

def get_editors_info(obj):
    """Получить информацию о редакторах объекта"""
    editors_info = []
    if obj.editors_allowed:
        for editor_id in obj.editors_allowed:
            user = User.query.get(editor_id)
            if user:
                editors_info.append({
                    'id': editor_id,
                    'username': user.username
                })
            else:
                editors_info.append({
                    'id': editor_id,
                    'username': 'Неизвестный пользователь'
                })
    return editors_info

@main_bp.route("/")
def index():
    return render_template("main.html.jinja", user=g.user)

@main_bp.route("/dashboard")
@login_required
def dashboard():
    user_classes = Class.query.filter_by(user_id=g.user.id).all()
    user_subclasses = Subclass.query.filter_by(user_id=g.user.id).all()
    user_races = Race.query.filter_by(user_id=g.user.id).all()
    user_foods = Food.query.filter_by(user_id=g.user.id).all()
    user_articles = Article.query.filter_by(user_id=g.user.id).all()
    return render_template('dashboard.html.jinja',
                         user=g.user,
                         user_classes=user_classes,
                         user_subclasses=user_subclasses,
                         user_races=user_races,
                         user_foods=user_foods,
                         user_articles=user_articles)

@main_bp.route("/grant_edit/<content_type>/<int:content_id>", methods=['GET', 'POST'])
@login_required
def grant_edit(content_type, content_id):
    if content_type == "class":
        obj = Class.query.get_or_404(content_id)
    elif content_type == "subclass":
        obj = Subclass.query.get_or_404(content_id)
    elif content_type == "race":
        obj = Race.query.get_or_404(content_id)
    elif content_type == "food":
        obj = Food.query.get_or_404(content_id)
    elif content_type == "article":
        obj = Article.query.get_or_404(content_id)
    else:
        flash("Тип контента не поддерживается.", "danger")
        return redirect(url_for('main.index'))

    form = GrantEditForm()
    if form.validate_on_submit():
        username = form.username.data
        user = User.query.filter_by(username=username).first()
        if not user:
            flash("Пользователь не найден.", "danger")
        else:
            # Используем правильное поле editors_allowed
            if not obj.editors_allowed:
                obj.editors_allowed = []
            
            current_editors = obj.editors_allowed.copy() if obj.editors_allowed else []
            if user.id not in current_editors:
                current_editors.append(user.id)
                obj.editors_allowed = current_editors
                db.session.commit()
                flash(f"Права на редактирование выданы пользователю {username}.", "success")
            else:
                flash(f"Пользователь {username} уже имеет права на редактирование.", "info")
        return redirect(request.url)

    return render_template(
        "grant_edit.html.jinja",
        content_type=content_type,
        content_id=content_id,
        content_object=obj,
        form=form,
        editors_info=get_editors_info(obj)
    )
