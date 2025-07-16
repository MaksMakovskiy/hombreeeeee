# main.py

from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, IntegerField, SelectField, FieldList, FormField, HiddenField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, NumberRange
import os
import json
from flask import g
from markupsafe import Markup

# Импортируем все из crud.py
from crud import db, User, Class, Subclass, Ability, Comment, ClassTableRow, \
                 create_user, get_user_by_username, get_user_by_id, \
                 update_user_password, delete_user, \
                 get_all_classes, get_all_subclasses, add_comment, \
                 is_allowed_to_edit, grant_edit_permission # Новые импорты

app = Flask(__name__)

app.config['SECRET_KEY'] = 'очень_сложный_секретный_ключ_для_проекта_dnd_2025_07_05' # Смените это!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
with app.app_context():
    db.create_all()
# --- Существующие Формы ---
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

class UpdatePasswordForm(FlaskForm):
    current_password = PasswordField('Текущий пароль', validators=[DataRequired()])
    new_password = PasswordField('Новый пароль', validators=[DataRequired(), Length(min=6)])
    confirm_new_password = PasswordField('Подтвердите новый пароль', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Обновить пароль')

class CommentForm(FlaskForm):
    text = TextAreaField('Ваш комментарий', validators=[DataRequired(), Length(min=5, max=500)])
    submit = SubmitField('Оставить комментарий')

class GrantPermissionForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    submit = SubmitField('Выдать права на редактирование')

# --- НОВЫЕ ФОРМЫ для Классов, Подклассов, Способностей ---

class AbilityForm(FlaskForm):
    """Форма для одной способности, может быть вложенной."""
    name = StringField('Название способности', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Описание способности', validators=[DataRequired()])
    level = IntegerField('Уровень', validators=[DataRequired(), NumberRange(min=1, max=20)]) # D&D до 20 уровня
    type = SelectField('Тип', choices=[
        ('active', 'Активная'),
        ('passive', 'Пассивная'),
        ('feature', 'Особенность'),
        ('spell', 'Заклинание'),
        ('other', 'Другое')
    ], validators=[DataRequired()])
    # Для вложенности, но это сложно обрабатывать в WTForms, часто проще JS
    # children = FieldList(FormField('AbilityForm'), min_entries=0)
    # submit_ability = SubmitField('Добавить способность') # Это будет кнопка через JS

class BaseContentForm(FlaskForm):
    """Базовая форма для класса/подкласса."""
    name = StringField('Название', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Описание', validators=[DataRequired()])
    # abilities_json_field будет использоваться для передачи JSON данных о способностях
    # Это упрощает обработку динамических полей, созданных JS
    abilities_json_field = TextAreaField('Способности (JSON)', render_kw={'style': 'display: none;'})
    submit = SubmitField('Сохранить')

class ClassForm(BaseContentForm):
    """Форма для создания/редактирования Класса."""
    name = StringField('Название', validators=[DataRequired()])
    description = TextAreaField('Описание', validators=[DataRequired()])
    hit_dice = StringField('Кость хитов', validators=[DataRequired()])
    hit_points_first = StringField('Хиты на 1 уровне', validators=[DataRequired()])
    hit_points_next = StringField('Хиты на следующих уровнях', validators=[DataRequired()])
    armor_proficiencies = StringField('Доспехи', validators=[DataRequired()])
    weapon_proficiencies = StringField('Оружие', validators=[DataRequired()])
    tool_proficiencies = StringField('Инструменты', validators=[DataRequired()])
    saving_throws = StringField('Спасброски', validators=[DataRequired()])
    skills = StringField('Навыки', validators=[DataRequired()])
    abilities_json_field = HiddenField('Способности (JSON)')

class SubclassForm(BaseContentForm):
    """Форма для создания/редактирования Подкласса."""
    # Выбор родительского класса
    class_id = SelectField('Родительский Класс', coerce=int, validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_id.choices = [(c.id, c.name) for c in Class.query.order_by(Class.name).all()]
        if not self.class_id.choices:
            self.class_id.choices = [(0, 'Сначала создайте класс')] # Заглушка, если классов нет

# --- Вспомогательные функции для аутентификации ---
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему, чтобы получить доступ к этой странице.', 'info')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def editor_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(class_id, *args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            flash('Вы не авторизованы.', 'danger')
            return redirect(url_for('login'))

        content_type = request.path.split('/')[1] # 'classes' or 'subclasses'

        if content_type == 'classes':
            content_object = Class.query.get_or_404(class_id)
        elif content_type == 'subclasses':
            content_object = Subclass.query.get_or_404(class_id)
        else:
            abort(404) # Неизвестный тип контента

        if not is_allowed_to_edit(user_id, content_object):
            flash('У вас нет прав на редактирование этого контента.', 'danger')
            abort(403) # Forbidden
        return f(class_id, *args, **kwargs)
    return decorated_function

# --- Маршруты Flask ---

@app.before_request
def load_logged_in_user():
    """Загружает текущего пользователя для использования в шаблонах."""
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None # g - это объект, специфичный для запроса, глобально доступный в Flask
    else:
        g.user = get_user_by_id(user_id)

@app.route("/")
def index():
    # g.user уже загружен в @app.before_request
    return render_template("main.html.jinja", user=g.user)

@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = create_user(form.username.data, form.password.data)
        if user:
            flash('Ваш аккаунт успешно создан! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Ошибка регистрации: имя пользователя уже занято.', 'danger')
    return render_template('register.html.jinja', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = get_user_by_username(form.username.data)
        if user and user.check_password(form.password.data):
            session['user_id'] = user.id
            flash('Вы успешно вошли в систему!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Неверное имя пользователя или пароль.', 'danger')
    return render_template('login.html.jinja', form=form)

@app.route("/logout")
def logout():
    session.pop('user_id', None)
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))

@app.route("/dashboard")
@login_required
def dashboard():
    user = get_user_by_id(session['user_id'])
    # Получаем классы и подклассы, которые создал текущий пользователь
    user_classes = Class.query.filter_by(user_id=user.id).all()
    user_subclasses = Subclass.query.filter_by(user_id=user.id).all()
    return render_template('dashboard.html.jinja', user=user,
                           user_classes=user_classes, user_subclasses=user_subclasses)

@app.route("/profile/update", methods=['GET', 'POST'])
@login_required
def update_profile():
    user = get_user_by_id(session['user_id'])
    form = UpdatePasswordForm()
    if form.validate_on_submit():
        if user.check_password(form.current_password.data):
            if update_user_password(user.id, form.new_password.data):
                flash('Пароль успешно обновлен!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Ошибка при обновлении пароля.', 'danger')
        else:
            flash('Текущий пароль неверен.', 'danger')
    return render_template('update_profile.html.jinja', form=form, user=user)

@app.route("/profile/delete", methods=['POST'])
@login_required
def delete_profile():
    user_id = session['user_id']
    if delete_user(user_id): # Эта функция удалит и связанные объекты, если CASCADE настроен правильно
        session.pop('user_id', None)
        flash('Ваш аккаунт был успешно удален.', 'success')
        return redirect(url_for('index'))
    else:
        flash('Ошибка при удалении аккаунта.', 'danger')
        return redirect(url_for('dashboard'))


# --- НОВЫЕ МАРШРУТЫ ДЛЯ КЛАССОВ И ПОДКЛАССОВ ---
@app.route("/classes")
def list_classes():
    classes = get_all_classes()
    return render_template('list_classes.html.jinja', classes=classes, user=g.user)

# --- Создание класса с инициализацией таблицы уровней ---
@app.route("/classes/create", methods=['GET', 'POST'])
@login_required
def create_class():
    form = ClassForm()
    if form.validate_on_submit():
        try:
            abilities_data = json.loads(form.abilities_json_field.data)
        except json.JSONDecodeError:
            flash('Ошибка в формате данных способностей.', 'danger')
            return render_template('create_edit_class.html.jinja', form=form, mode='create', existing_abilities_json='[]')

        new_class = Class(
            name=form.name.data,
            description=form.description.data,
            user_id=session['user_id'],
            custom_columns_json=json.dumps([]),
            hit_dice = form.hit_dice.data,
            hit_points_first = form.hit_points_first.data,
            hit_points_next = form.hit_points_next.data,
            armor_proficiencies = form.armor_proficiencies.data,
            weapon_proficiencies = form.weapon_proficiencies.data,
            tool_proficiencies = form.tool_proficiencies.data,
            saving_throws = form.saving_throws.data,
            skills = form.skills.data
        )
        db.session.add(new_class)
        db.session.commit()

        # Создаем 20 строк таблицы уровней с бонусом мастерства
        proficiency_by_level = [2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,6,6,6,6]
        for lvl in range(1, 21):
            row = ClassTableRow(
                class_id=new_class.id,
                level=lvl,
                proficiency_bonus=proficiency_by_level[lvl-1],
                custom={}
            )
            db.session.add(row)
        db.session.commit()

        # Создаем способности
        for ability_data in abilities_data:
            ability = Ability(
                name=ability_data['name'],
                description=ability_data['description'],
                level=ability_data['level'],
                type=ability_data['type'],
                class_id=new_class.id
            )
            db.session.add(ability)
        db.session.commit()

        flash('Класс успешно создан!', 'success')
        return redirect(url_for('view_class', class_id=new_class.id))
    return render_template(
        'create_edit_class.html.jinja',
        form=form,
        mode='create',
        existing_abilities_json=json.dumps([])
    )

@app.route("/classes/<int:class_id>")
def view_class(class_id):
    current_class = Class.query.get_or_404(class_id)
    comment_form = CommentForm()
    abilities = Ability.query.filter_by(class_id=class_id, parent_id=None).order_by(Ability.level).all()
    can_edit = is_allowed_to_edit(session.get('user_id'), current_class)
    # Получаем таблицу уровней и пользовательские колонки
    class_table = ClassTableRow.query.filter_by(class_id=current_class.id).order_by(ClassTableRow.level).all()
    custom_columns = json.loads(current_class.custom_columns_json or "[]")
    return render_template(
        'view_class.html.jinja',
        current_class=current_class,
        abilities=abilities,
        class_table=class_table,
        custom_columns=custom_columns,
        comment_form=comment_form,
        can_edit=can_edit
    )

@app.route("/classes/<int:class_id>/edit", methods=['GET', 'POST'])
@login_required
@editor_required
def edit_class(class_id):
    # Retrieve the class or return 404 if not found
    current_class = Class.query.get_or_404(class_id)
    # Populate the form with current class data
    form = ClassForm(obj=current_class)

    # Get existing abilities for JavaScript
    existing_abilities = []
    for ab in Ability.query.filter_by(class_id=class_id, parent_id=None).order_by(Ability.level).all():
        existing_abilities.append({
            'id': ab.id,
            'name': ab.name,
            'description': ab.description,
            'level': ab.level,
            'type': ab.type,
            'custom_columns': ab.custom_table if ab.custom_table else {}
        })

    # Process form submission
    if form.validate_on_submit():
        try:
            # Parse abilities data from JSON field
            abilities_data = json.loads(form.abilities_json_field.data)
        except json.JSONDecodeError:
            flash('Ошибка в формате данных способностей.', 'danger')
            return render_template('create_edit_class.html.jinja', form=form, mode='edit', content_id=class_id, existing_abilities_json=json.dumps(existing_abilities))

        # Update core class attributes from the form data
        current_class.name = form.name.data
        current_class.description = form.description.data
        current_class.hit_dice = form.hit_dice.data
        current_class.hit_points_first = form.hit_points_first.data
        current_class.hit_points_next = form.hit_points_next.data
        current_class.armor_proficiencies = form.armor_proficiencies.data
        current_class.weapon_proficiencies = form.weapon_proficiencies.data
        current_class.tool_proficiencies = form.tool_proficiencies.data
        current_class.saving_throws = form.saving_throws.data
        current_class.skills = form.skills.data

        # Update abilities: delete old ones, add new ones
        # Using delete-orphan cascade on the relationship usually handles deletion more cleanly
        # If not using cascade="all, delete-orphan" on the relationship, this line is necessary:
        # Ability.query.filter_by(class_id=class_id).delete()
        # Instead, clear the relationship and re-add for better SQLAlchemy management of deletions/updates
        current_class.abilities = [] # This will delete old abilities if cascade="all, delete-orphan" is set on the relationship

        for ability_data in abilities_data:
            # Ensure proper data types, especially for 'level'
            try:
                level_val = int(ability_data.get('level', 1))
            except (ValueError, TypeError):
                level_val = 1 # Default to 1 if conversion fails

            ability = Ability(
                name=ability_data.get('name', ''),
                description=ability_data.get('description', ''),
                level=level_val,
                type=ability_data.get('type', ''),
                class_id=current_class.id
            )
            db.session.add(ability)

        db.session.commit()
        flash('Класс успешно обновлен!', 'success')
        return redirect(url_for('view_class', class_id=current_class.id))

    # Render the form on GET request or if validation fails
    return render_template('create_edit_class.html.jinja', form=form, mode='edit', content_id=class_id, existing_abilities_json=json.dumps(existing_abilities))


@app.route("/classes/<int:class_id>/delete", methods=['POST'])
@login_required
@editor_required
def delete_class(class_id):
    current_class = Class.query.get_or_404(class_id)
    # CASCADE на связях Class поможет удалить Abilities и Comments
    db.session.delete(current_class)
    db.session.commit()
    flash('Класс успешно удален!', 'success')
    return redirect(url_for('list_classes'))

@app.route("/classes/<int:class_id>/comment", methods=['POST'])
@login_required
def add_class_comment(class_id):
    form = CommentForm()
    if form.validate_on_submit():
        user_id = session['user_id']
        add_comment(user_id, form.text.data, class_id=class_id)
        flash('Комментарий добавлен!', 'success')
    else:
        flash('Ошибка при добавлении комментария.', 'danger')
    return redirect(url_for('view_class', class_id=class_id))

# --- Маршруты для Подклассов (аналогично классам) ---

@app.route("/subclasses")
def list_subclasses():
    subclasses = get_all_subclasses()
    return render_template('list_subclasses.html.jinja', subclasses=subclasses, user=g.user)

@app.route("/subclasses/create", methods=['GET', 'POST'])
@login_required
def create_subclass():
    form = SubclassForm()
    if form.validate_on_submit():
        try:
            abilities_data = json.loads(form.abilities_json_field.data)
        except json.JSONDecodeError:
            flash('Ошибка в формате данных способностей.', 'danger')
            return render_template('create_edit_subclass.html.jinja', form=form, mode='create')

        new_subclass = Subclass(
            name=form.name.data,
            description=form.description.data,
            user_id=session['user_id'],
            class_id=form.class_id.data
        )
        db.session.add(new_subclass)
        db.session.commit()

        for ability_data in abilities_data:
            ability = Ability(
                name=ability_data['name'],
                description=ability_data['description'],
                level=ability_data['level'],
                type=ability_data['type'],
                subclass_id=new_subclass.id # Привязываем к новому подклассу
            )
            db.session.add(ability)
        db.session.commit()

        flash('Подкласс успешно создан!', 'success')
        return redirect(url_for('view_subclass', subclass_id=new_subclass.id))
    return render_template('create_edit_subclass.html.jinja', form=form, mode='create')

@app.route("/subclasses/<int:subclass_id>")
def view_subclass(subclass_id):
    current_subclass = Subclass.query.get_or_404(subclass_id)
    comment_form = CommentForm()
    abilities = Ability.query.filter_by(subclass_id=subclass_id, parent_id=None).order_by(Ability.level).all()

    can_edit = is_allowed_to_edit(session.get('user_id'), current_subclass)

    return render_template('view_subclass.html.jinja',
                           current_subclass=current_subclass,
                           abilities=abilities,
                           comment_form=comment_form,
                           user=g.user,
                           can_edit=can_edit)

@app.route("/subclasses/<int:subclass_id>/edit", methods=['GET', 'POST'])
@login_required
@editor_required
def edit_subclass(subclass_id):
    current_subclass = Subclass.query.get_or_404(subclass_id)
    form = SubclassForm(obj=current_subclass)
    # Важно: для SelectField нужно переопределить choices после инициализации form(obj=...)
    form.class_id.choices = [(c.id, c.name) for c in Class.query.order_by(Class.name).all()]

    existing_abilities = []
    for ab in Ability.query.filter_by(subclass_id=subclass_id, parent_id=None).order_by(Ability.level).all():
        existing_abilities.append({
            'id': ab.id,
            'name': ab.name,
            'description': ab.description,
            'level': ab.level,
            'type': ab.type
        })

    if form.validate_on_submit():
        try:
            abilities_data = json.loads(form.abilities_json_field.data)
        except json.JSONDecodeError:
            flash('Ошибка в формате данных способностей.', 'danger')
            return render_template('create_edit_subclass.html.jinja', form=form, mode='edit', content_id=subclass_id, existing_abilities_json=json.dumps(existing_abilities))

        current_subclass.name = form.name.data
        current_subclass.description = form.description.data
        current_subclass.class_id = form.class_id.data

        Ability.query.filter_by(subclass_id=subclass_id).delete()
        for ability_data in abilities_data:
            ability = Ability(
                name=ability_data['name'],
                description=ability_data['description'],
                level=ability_data['level'],
                type=ability_data['type'],
                subclass_id=current_subclass.id
            )
            db.session.add(ability)

        db.session.commit()
        flash('Подкласс успешно обновлен!', 'success')
        return redirect(url_for('view_subclass', subclass_id=current_subclass.id))

    return render_template('create_edit_subclass.html.jinja', form=form, mode='edit', content_id=subclass_id, existing_abilities_json=json.dumps(existing_abilities))


@app.route("/subclasses/<int:subclass_id>/delete", methods=['POST'])
@login_required
@editor_required
def delete_subclass(subclass_id):
    current_subclass = Subclass.query.get_or_404(subclass_id)
    db.session.delete(current_subclass)
    db.session.commit()
    flash('Подкласс успешно удален!', 'success')
    return redirect(url_for('list_subclasses'))

@app.route("/subclasses/<int:subclass_id>/comment", methods=['POST'])
@login_required
def add_subclass_comment(subclass_id):
    form = CommentForm()
    if form.validate_on_submit():
        user_id = session['user_id']
        add_comment(user_id, form.text.data, subclass_id=subclass_id)
        flash('Комментарий добавлен!', 'success')
    else:
        flash('Ошибка при добавлении комментария.', 'danger')
    return redirect(url_for('view_subclass', subclass_id=subclass_id))

# --- Маршрут для Еды (простой пример) ---
@app.route("/food")
def food_page():
    return render_template('food.html.jinja', user=g.user)

# --- Маршрут для выдачи прав на редактирование ---

@app.route("/grant_edit/<content_type>/<int:content_id>", methods=['GET', 'POST'])
@login_required
def grant_edit(content_type, content_id):
    current_user_id = session['user_id']
    content_object = None

    if content_type == 'class':
        content_object = Class.query.get_or_404(content_id)
        redirect_url = url_for('view_class', class_id=content_id)
    elif content_type == 'subclass':
        content_object = Subclass.query.get_or_404(content_id)
        redirect_url = url_for('view_subclass', subclass_id=content_id)
    else:
        abort(404)

    # Проверка, что текущий пользователь является автором или имеет права на выдачу
    if not is_allowed_to_edit(current_user_id, content_object):
        flash('У вас нет прав на выдачу разрешений для этого контента.', 'danger')
        return redirect(redirect_url)

    form = GrantPermissionForm()
    if form.validate_on_submit():
        target_username = form.username.data
        target_user = get_user_by_username(target_username)

        if not target_user:
            flash(f'Пользователь с именем "{target_username}" не найден.', 'danger')
        elif target_user.id == current_user_id:
            flash('Вы не можете выдать права самому себе.', 'warning')
        else:
            success, message = grant_edit_permission(target_user.id, content_object, current_user_id)
            flash(message, 'success' if success else 'danger')
            return redirect(redirect_url) # Вернуться на страницу контента после выдачи

    return render_template('grant_edit.html.jinja', form=form, content_type=content_type, content_object=content_object)

@app.context_processor
def inject_user():
    from flask import g
    return dict(user=getattr(g, 'user', None))

@app.template_filter('nl2br')
def nl2br(value):
    return Markup(value.replace('\n', '<br>'))

@app.route("/races")
def list_races():
    # TODO: Реализуйте получение всех рас
    races = []  # Заглушка
    return render_template('list_races.html.jinja', races=races)

@app.route("/races/create", methods=['GET', 'POST'])
@login_required
def create_race():
    # TODO: Реализуйте форму создания расы
    if request.method == 'POST':
        # Логика создания расы
        flash('Раса успешно создана!', 'success')
        return redirect(url_for('list_races'))
    return render_template('create_edit_race.html.jinja', mode='create')

@app.route("/classes/<int:class_id>/table/edit/<int:level>", methods=['POST'])
@login_required
@editor_required
def edit_class_table_row(content_id, level):
    row = ClassTableRow.query.filter_by(class_id=content_id, level=level).first_or_404()
    # Меняем только бонус мастерства и пользовательские поля
    if 'proficiency_bonus' in request.form:
        row.proficiency_bonus = int(request.form['proficiency_bonus'])
    # Обновить пользовательские поля
    class_obj = Class.query.get_or_404(content_id)
    custom_columns = json.loads(class_obj.custom_columns_json or "[]")
    custom = row.custom or {}
    for col in custom_columns:
        key = f"custom_{col}"
        if key in request.form:
            custom[col] = request.form[key]
    row.custom = custom
    db.session.commit()
    return redirect(url_for('view_class', class_id=content_id))

# --- Добавление пользовательской колонки в таблицу уровней ---
@app.route("/classes/<int:class_id>/table/add_column", methods=['POST'])
@login_required
@editor_required
def add_class_table_column(class_id):
    class_obj = Class.query.get_or_404(class_id)
    custom_columns = json.loads(class_obj.custom_columns_json or "[]")
    new_col = request.form['column_name'].strip()
    if new_col and new_col not in custom_columns:
        custom_columns.append(new_col)
        class_obj.custom_columns_json = json.dumps(custom_columns)
        db.session.commit()
    return redirect(url_for('view_class', class_id=class_id))



# --- Запуск приложения ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=8989)