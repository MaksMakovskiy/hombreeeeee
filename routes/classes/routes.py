# routes/classes/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, HiddenField, SubmitField
from wtforms.validators import DataRequired, Length
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from crud import db, Class, Ability, ClassTableRow, add_comment, is_allowed_to_edit
from utils.decorators import login_required, editor_required
from forms.comments import CommentForm
import json

classes_bp = Blueprint('classes', __name__, url_prefix='/classes')

# Перенести формы из основного файла
class ClassForm(FlaskForm):
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

@classes_bp.route("/")
def list_classes():
    classes = Class.query.all()
    return render_template('list_classes.html.jinja', classes=classes)

@classes_bp.route("/create", methods=['GET', 'POST'])
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
        return redirect(url_for('classes.view_class', class_id=new_class.id))
    return render_template(
        'create_edit_class.html.jinja',
        form=form,
        mode='create',
        existing_abilities_json=json.dumps([])
    )

@classes_bp.route("/<int:class_id>")
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

@classes_bp.route("/<int:class_id>/edit", methods=['GET', 'POST'])
@login_required
@editor_required
def edit_class(class_id):
    current_class = Class.query.get_or_404(class_id)
    form = ClassForm(obj=current_class)
    class_table = ClassTableRow.query.filter_by(class_id=current_class.id).order_by(ClassTableRow.level).all()
    custom_columns = json.loads(current_class.custom_columns_json or "[]")
    existing_abilities = [
        {
            'id': ab.id,
            'name': ab.name,
            'description': ab.description,
            'level': ab.level,
            'type': ab.type
        }
        for ab in Ability.query.filter_by(class_id=class_id, parent_id=None).order_by(Ability.level).all()
    ]

    # Обработка удаления колонки через GET-параметр
    remove_column = request.args.get('remove_column')
    if remove_column and remove_column in custom_columns:
        custom_columns.remove(remove_column)
        current_class.custom_columns_json = json.dumps(custom_columns)
        # Удаляем значения этой колонки из всех строк таблицы
        for row in class_table:
            if remove_column in row.custom:
                row.custom.pop(remove_column)
        db.session.commit()
        flash(f'Колонка "{remove_column}" удалена.', 'success')
        return redirect(url_for('classes.edit_class', class_id=class_id))

    if form.validate_on_submit():
        try:
            abilities_data = json.loads(form.abilities_json_field.data or "[]")
            # Обработка кастомных колонок
            if 'custom_columns' in request.form:
                new_custom_columns = json.loads(request.form['custom_columns'])
                current_class.custom_columns_json = json.dumps(new_custom_columns)
                custom_columns = new_custom_columns
            # Обработка таблицы
            if 'table_data' in request.form:
                table_data = json.loads(request.form['table_data'])
                for row_data in table_data:
                    row = ClassTableRow.query.filter_by(class_id=class_id, level=row_data['level']).first()
                    if row:
                        row.proficiency_bonus = row_data['proficiency_bonus']
                        # Сохраняем значения только для колонок из custom_columns
                        custom_data = {col: row_data.get('custom', {}).get(col, '') for col in custom_columns}
                        row.custom = custom_data
            # Обновление остальных полей
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
            current_class.abilities = []
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
                    class_id=current_class.id
                )
                db.session.add(ability)
            db.session.commit()
            flash('Класс успешно обновлен!', 'success')
            return redirect(url_for('classes.view_class', class_id=current_class.id))
        except json.JSONDecodeError:
            flash('Ошибка в формате данных.', 'danger')
    return render_template('create_edit_class.html.jinja',
                         form=form,
                         mode='edit',
                         content_id=class_id,
                         class_table=class_table,
                         custom_columns=custom_columns,
                         existing_abilities_json=json.dumps(existing_abilities))

@classes_bp.route("/<int:class_id>/delete", methods=['POST'])
@login_required
@editor_required
def delete_class(class_id):
    current_class = Class.query.get_or_404(class_id)
    # CASCADE на связях Class поможет удалить Abilities и Comments
    db.session.delete(current_class)
    db.session.commit()
    flash('Класс успешно удален!', 'success')
    return redirect(url_for('list_classes'))

@classes_bp.route("/<int:class_id>/comment", methods=['POST'])
@login_required
def add_class_comment(class_id):
    form = CommentForm()
    if form.validate_on_submit():
        user_id = session['user_id']
        add_comment(user_id, form.text.data, class_id=class_id)
        flash('Комментарий добавлен!', 'success')
    else:
        flash('Ошибка при добавлении комментария.', 'danger')
    return redirect(url_for('classes.view_class', class_id=class_id))

@classes_bp.route("/<int:class_id>/table/edit/<int:level>", methods=['POST'])
@login_required
@editor_required
def edit_class_table_row(class_id, level):
    row = ClassTableRow.query.filter_by(class_id=class_id, level=level).first_or_404()
    if 'proficiency_bonus' in request.form:
        row.proficiency_bonus = int(request.form['proficiency_bonus'])
    
    class_obj = Class.query.get_or_404(class_id)
    custom_columns = json.loads(class_obj.custom_columns_json or "[]")
    custom = row.custom or {}
    for col in custom_columns:
        key = f"custom_{col}"
        if key in request.form:
            custom[col] = request.form[key]
    row.custom = custom
    db.session.commit()
    return redirect(url_for('classes.view_class', class_id=class_id))

@classes_bp.route("/<int:class_id>/table/add_column", methods=['POST'])
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
    return redirect(url_for('classes.edit_class', class_id=class_id))