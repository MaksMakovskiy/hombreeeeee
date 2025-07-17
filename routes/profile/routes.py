from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo
from crud import get_user_by_id, update_user_password, delete_user, Class, Subclass, Race, Food, db
from utils.decorators import login_required
from forms.comments import ProfileForm
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
            return redirect(url_for('profile.view_profile'))
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

@profile_bp.route("/view", methods=['GET', 'POST'])
@login_required
def view_profile():
    user_id = session['user_id']
    user = get_user_by_id(user_id)
    form = ProfileForm()
    
    if form.validate_on_submit():
        # Обновляем данные пользователя
        user.username = form.username.data
        db.session.commit()
        flash('Профиль успешно обновлен!', 'success')
        return redirect(url_for('profile.view_profile'))
    
    # Заполняем форму текущими данными пользователя
    if request.method == 'GET':
        form.username.data = user.username
    
    # Получаем объекты пользователя и объекты, которые он может редактировать
    # Собственные объекты пользователя
    user_classes = Class.query.filter_by(user_id=user_id).all()
    user_subclasses = Subclass.query.filter_by(user_id=user_id).all()
    user_races = Race.query.filter_by(user_id=user_id).all()
    user_foods = Food.query.filter_by(user_id=user_id).all()
    
    # Объекты, которые пользователь может редактировать (но не создавал сам)
    editable_classes = []
    editable_subclasses = []
    editable_races = []
    editable_foods = []
    
    # Для каждого типа объектов проверяем права доступа
    for cls in Class.query.filter(Class.user_id != user_id).all():
        if cls.editors_allowed and user_id in cls.editors_allowed:
            editable_classes.append(cls)
    
    for subcls in Subclass.query.filter(Subclass.user_id != user_id).all():
        if subcls.editors_allowed and user_id in subcls.editors_allowed:
            editable_subclasses.append(subcls)
    
    for race in Race.query.filter(Race.user_id != user_id).all():
        if race.editors_allowed and user_id in race.editors_allowed:
            editable_races.append(race)
    
    for food in Food.query.filter(Food.user_id != user_id).all():
        if food.editors_allowed and user_id in food.editors_allowed:
            editable_foods.append(food)
    
    return render_template(
        'profile.html.jinja',
        form=form,
        user=user,
        user_classes=user_classes,
        user_subclasses=user_subclasses,
        user_races=user_races,
        user_foods=user_foods,
        editable_classes=editable_classes,
        editable_subclasses=editable_subclasses,
        editable_races=editable_races,
        editable_foods=editable_foods
    )

@profile_bp.route("/view_user/<username>")
@login_required
def view_user_profile(username):
    """Просмотр профиля другого пользователя"""
    from crud import User
    user = User.query.filter_by(username=username).first()
    if not user:
        flash(f'Пользователь {username} не найден.', 'danger')
        return redirect(url_for('profile.view_profile'))
    
    # Получаем созданные пользователем объекты (публичные)
    user_classes = Class.query.filter_by(user_id=user.id).all()
    user_subclasses = Subclass.query.filter_by(user_id=user.id).all()
    user_races = Race.query.filter_by(user_id=user.id).all()
    user_foods = Food.query.filter_by(user_id=user.id).all()
    
    return render_template(
        'view_user_profile.html.jinja',
        viewed_user=user,
        user_classes=user_classes,
        user_subclasses=user_subclasses,
        user_races=user_races,
        user_foods=user_foods
    )
