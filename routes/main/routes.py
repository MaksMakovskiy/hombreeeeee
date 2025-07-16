from flask import Blueprint, render_template, redirect, url_for, g, request, flash, session
from crud import db, Class, Subclass, User
from utils.decorators import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import json

main_bp = Blueprint('main', __name__)

class GrantEditForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    submit = SubmitField('Выдать права')

@main_bp.route("/")
def index():
    return render_template("main.html.jinja", user=g.user)

@main_bp.route("/dashboard")
@login_required
def dashboard():
    user_classes = Class.query.filter_by(user_id=g.user.id).all()
    user_subclasses = Subclass.query.filter_by(user_id=g.user.id).all()
    return render_template('dashboard.html.jinja',
                         user=g.user,
                         user_classes=user_classes,
                         user_subclasses=user_subclasses)

@main_bp.route("/grant_edit/<content_type>/<int:content_id>", methods=['GET', 'POST'])
@login_required
def grant_edit(content_type, content_id):
    if content_type == "class":
        obj = Class.query.get_or_404(content_id)
    elif content_type == "subclass":
        obj = Subclass.query.get_or_404(content_id)
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
            # Пример: добавляем user_id в список редакторов (реализуйте хранение прав в модели)
            if not hasattr(obj, "editors"):
                obj.editors = []
            if user.id not in obj.editors:
                obj.editors.append(user.id)
                # Сохраните editors в БД, например, как JSON-строку
                obj.editors_json = json.dumps(obj.editors)
                db.session.commit()
            flash(f"Права на редактирование выданы пользователю {username}.", "success")
        return redirect(request.url)

    return render_template(
        "grant_edit.html.jinja",
        content_type=content_type,
        content_id=content_id,
        content_object=obj,
        form=form
    )
