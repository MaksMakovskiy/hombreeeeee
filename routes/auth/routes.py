# routes/auth/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo
from crud import db, User, get_user_by_username, create_user, get_user_by_id

auth_bp = Blueprint('auth', __name__)

class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Подтвердите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

    def validate_username(self, username):
        user = get_user_by_username(username.data)
        if user:
            raise ValidationError('Это имя пользователя уже занято. Пожалуйста, выберите другое.')

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class LogoutForm(FlaskForm):
    submit = SubmitField('Выйти')

@auth_bp.before_app_request
def load_logged_in_user():
    """Загружает текущего пользователя для использования в шаблонах."""
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None # g - это объект, специфичный для запроса, глобально доступный в Flask
    else:
        g.user = get_user_by_id(user_id)

@auth_bp.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Ваш аккаунт успешно создан! Теперь вы можете войти.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html.jinja', form=form)

@auth_bp.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = get_user_by_username(form.username.data)
        if user and user.check_password(form.password.data):
            session['user_id'] = user.id
            flash('Вы успешно вошли в систему!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Неверное имя пользователя или пароль.', 'danger')
    return render_template('login.html.jinja', form=form)

@auth_bp.route("/logout", methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        form = LogoutForm()
        if form.validate_on_submit():
            session.pop('user_id', None)
            flash('Вы вышли из системы.', 'info')
            return redirect(url_for('main.index'))
    # Для GET запросов (прямая ссылка)
    session.pop('user_id', None)
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('main.index'))