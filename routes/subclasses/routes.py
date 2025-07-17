from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, HiddenField, SubmitField
from wtforms.validators import DataRequired, Length
from crud import db, Subclass, Ability, Class, add_comment, is_allowed_to_edit
from utils.decorators import login_required, editor_required
from forms.comments import CommentForm
import json

subclasses_bp = Blueprint('subclasses', __name__, url_prefix='/subclasses')

class SubclassForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Описание', validators=[DataRequired()])
    class_id = SelectField('Родительский Класс', coerce=int, validators=[DataRequired()])
    abilities_json_field = HiddenField('Способности (JSON)')
    submit = SubmitField('Сохранить')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_id.choices = [(c.id, c.name) for c in Class.query.order_by(Class.name).all()]
        if not self.class_id.choices:
            self.class_id.choices = [(0, 'Сначала создайте класс')]

@subclasses_bp.route("/")
def list_subclasses():
    subclasses = Subclass.query.all()  # Показываем все подклассы
    return render_template('list_subclasses.html.jinja', subclasses=subclasses)

@subclasses_bp.route("/create", methods=['GET', 'POST'])
@login_required
def create_subclass():
    form = SubclassForm()
    if form.validate_on_submit():
        try:
            abilities_data = json.loads(form.abilities_json_field.data or "[]")
        except json.JSONDecodeError:
            flash('Ошибка в формате данных способностей.', 'danger')
            return render_template('create_edit_subclass.html.jinja', form=form, mode='create')

        # Проверка что выбран корректный класс
        if form.class_id.data == 0:
            flash('Выберите родительский класс.', 'danger')
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
                name=ability_data.get('name', ''),
                description=ability_data.get('description', ''),
                level=ability_data.get('level', 1),
                type=ability_data.get('type', ''),
                subclass_id=new_subclass.id
            )
            db.session.add(ability)
        db.session.commit()

        flash('Подкласс успешно создан!', 'success')
        return redirect(url_for('subclasses.view_subclass', subclass_id=new_subclass.id))
    return render_template('create_edit_subclass.html.jinja', form=form, mode='create')

@subclasses_bp.route("/<int:subclass_id>")
def view_subclass(subclass_id):
    current_subclass = Subclass.query.get_or_404(subclass_id)
    comment_form = CommentForm()
    abilities = Ability.query.filter_by(subclass_id=subclass_id, parent_id=None).order_by(Ability.level).all()
    can_edit = is_allowed_to_edit(session.get('user_id'), current_subclass)
    return render_template('view_subclass.html.jinja',
                         current_subclass=current_subclass,
                         abilities=abilities,
                         comment_form=comment_form,
                         can_edit=can_edit)

@subclasses_bp.route("/<int:subclass_id>/comment", methods=['POST'])
@login_required
def add_subclass_comment(subclass_id):
    form = CommentForm()
    if form.validate_on_submit():
        user_id = session['user_id']
        add_comment(user_id, form.text.data, subclass_id=subclass_id)
        flash('Комментарий добавлен!', 'success')
    else:
        flash('Ошибка при добавлении комментария.', 'danger')
    return redirect(url_for('subclasses.view_subclass', subclass_id=subclass_id))

@subclasses_bp.route("/<int:subclass_id>/edit", methods=['GET', 'POST'])
@login_required
@editor_required
def edit_subclass(subclass_id):
    current_subclass = Subclass.query.get_or_404(subclass_id)
    form = SubclassForm(obj=current_subclass)
    
    # Загружаем существующие способности
    existing_abilities = [
        {
            'id': ab.id,
            'name': ab.name,
            'description': ab.description,
            'level': ab.level,
            'type': ab.type
        }
        for ab in Ability.query.filter_by(subclass_id=subclass_id).order_by(Ability.level).all()
    ]

    if form.validate_on_submit():
        try:
            abilities_data = json.loads(form.abilities_json_field.data or "[]")
        except json.JSONDecodeError:
            flash('Ошибка в формате данных способностей.', 'danger')
            return render_template('create_edit_subclass.html.jinja', form=form, mode='edit', 
                                 content_id=subclass_id, content_object=current_subclass, existing_abilities=existing_abilities)

        # Проверка что выбран корректный класс
        if form.class_id.data == 0:
            flash('Выберите родительский класс.', 'danger')
            return render_template('create_edit_subclass.html.jinja', form=form, mode='edit',
                                 content_id=subclass_id, content_object=current_subclass, existing_abilities=existing_abilities)

        # Обновление основной информации
        current_subclass.name = form.name.data
        current_subclass.description = form.description.data
        current_subclass.class_id = form.class_id.data

        # Удаляем старые способности и добавляем новые
        old_abilities = Ability.query.filter_by(subclass_id=subclass_id).all()
        for ab in old_abilities:
            db.session.delete(ab)

        # Добавляем новые способности
        for ability_data in abilities_data:
            try:
                level_val = int(ability_data.get('level', 1))
            except (ValueError, TypeError):
                level_val = 1
            
            ability = Ability(
                name=ability_data.get('name', ''),
                description=ability_data.get('description', ''),
                level=level_val,
                type=ability_data.get('type', ''),
                subclass_id=current_subclass.id
            )
            db.session.add(ability)

        db.session.commit()
        flash('Подкласс успешно обновлен!', 'success')
        return redirect(url_for('subclasses.view_subclass', subclass_id=current_subclass.id))

    return render_template('create_edit_subclass.html.jinja',
                         form=form,
                         mode='edit',
                         content_id=subclass_id,
                         content_object=current_subclass,
                         existing_abilities=existing_abilities)

@subclasses_bp.route("/<int:subclass_id>/delete", methods=['POST'])
@login_required
@editor_required
def delete_subclass(subclass_id):
    current_subclass = Subclass.query.get_or_404(subclass_id)
    
    # Удаляем связанные способности
    abilities = Ability.query.filter_by(subclass_id=subclass_id).all()
    for ability in abilities:
        db.session.delete(ability)
    
    # Удаляем сам подкласс
    db.session.delete(current_subclass)
    db.session.commit()
    
    flash(f'Подкласс "{current_subclass.name}" успешно удален.', 'success')
    return redirect(url_for('subclasses.list_subclasses'))
