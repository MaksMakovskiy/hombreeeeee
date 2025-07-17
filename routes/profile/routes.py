from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo
from crud import get_user_by_id, update_user_password, delete_user, Class, Subclass, Race, Food
from utils.decorators import login_required
import json

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

class UpdatePasswordForm(FlaskForm):
    current_password = PasswordField('Текущий пароль', validators=[DataRequired()])
    new_password = PasswordField('Новый пароль', validators=[DataRequired(), Length(min=6)])
    confirm_new_password = PasswordField('Подтвердите новый пароль', 
                                       validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Обновить пароль')

@profile_bp.route("/update", methods=['GET', 'POST'])
@login_required
def update_profile():
    user = get_user_by_id(session['user_id'])
    form = UpdatePasswordForm()
    if form.validate_on_submit():
        if user.check_password(form.current_password.data):
            user.set_password(form.new_password.data)
            db.session.commit()
            flash('Пароль успешно обновлен!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Текущий пароль неверен.', 'danger')
    return render_template('update_profile.html.jinja', form=form, user=user)

@profile_bp.route("/delete", methods=['POST'])
@login_required
def delete_profile():
    if delete_user(session['user_id']):
        session.pop('user_id', None)
        flash('Ваш аккаунт был успешно удален.', 'success')
        return redirect(url_for('main.index'))
    flash('Ошибка при удалении аккаунта.', 'danger')
    return redirect(url_for('profile.dashboard'))
    return redirect(url_for('profile.dashboard'))

@profile_bp.route("/view", methods=['GET'])
@login_required
def view_profile():
    user_id = session['user_id']
    user = get_user_by_id(user_id)
    # Получаем объекты, которые пользователь может редактировать
    classes = Class.query.filter(Class.editors_allowed.contains([user_id])).all()
    subclasses = Subclass.query.filter(Subclass.editors_allowed.contains([user_id])).all()
    races = Race.query.filter(Race.editors_allowed.contains([user_id])).all()
    foods = Food.query.filter(Food.editors_allowed.contains([user_id])).all()
    return render_template(
        'profile.html.jinja',
        user=user,
        editable_classes=classes,
        editable_subclasses=subclasses,
        editable_races=races,
        editable_foods=foods
    )
