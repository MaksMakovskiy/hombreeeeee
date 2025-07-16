from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, HiddenField, SubmitField
from wtforms.validators import DataRequired
from crud import db, Race, RaceAbility, User
from utils.decorators import login_required, editor_required
import json

races_bp = Blueprint('races', __name__, url_prefix='/races')

class RaceForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    description = TextAreaField('Описание', validators=[DataRequired()])
    image_url = StringField('URL картинки')
    abilities_json_field = HiddenField('Умения (JSON)')
    submit = SubmitField('Сохранить')

@races_bp.route("/")
def list_races():
    races = Race.query.all()
    return render_template('list_races.html.jinja', races=races)

@races_bp.route("/create", methods=['GET', 'POST'])
@login_required
def create_race():
    form = RaceForm()
    if form.validate_on_submit():
        try:
            abilities_data = json.loads(form.abilities_json_field.data or "[]")
        except json.JSONDecodeError:
            flash('Ошибка в формате данных умений.', 'danger')
            return render_template('create_edit_race.html.jinja', form=form, mode='create')
        new_race = Race(
            name=form.name.data,
            description=form.description.data,
            image_url=form.image_url.data,
            user_id=session['user_id'],
            editors_allowed=[session['user_id']]
        )
        db.session.add(new_race)
        db.session.commit()
        for ability_data in abilities_data:
            ability = RaceAbility(
                race_id=new_race.id,
                name=ability_data.get('name', ''),
                description=ability_data.get('description', '')
            )
            db.session.add(ability)
        db.session.commit()
        flash('Раса успешно создана!', 'success')
        return redirect(url_for('races.view_race', race_id=new_race.id))
    return render_template('create_edit_race.html.jinja', form=form, mode='create')

@races_bp.route("/<int:race_id>")
def view_race(race_id):
    race = Race.query.get_or_404(race_id)
    abilities = RaceAbility.query.filter_by(race_id=race_id).all()
    can_edit = session.get('user_id') in (race.editors_allowed or [])
    return render_template('view_race.html.jinja', race=race, abilities=abilities, can_edit=can_edit)

@races_bp.route("/grant_edit/<int:race_id>", methods=['GET', 'POST'])
@login_required
def grant_edit_race(race_id):
    race = Race.query.get_or_404(race_id)
    if request.method == "POST":
        username = request.form.get("username")
        user = User.query.filter_by(username=username).first()
        if not user:
            flash("Пользователь не найден.", "danger")
        else:
            if user.id not in (race.editors_allowed or []):
                race.editors_allowed.append(user.id)
                db.session.commit()
            flash(f"Права на редактирование выданы пользователю {username}.", "success")
        return redirect(request.url)
    return render_template("grant_edit_race.html.jinja", race=race)

@races_bp.route("/<int:race_id>/edit", methods=['GET', 'POST'])
@login_required
def edit_race(race_id):
    race = Race.query.get_or_404(race_id)
    # Проверка прав на редактирование
    user_id = session.get('user_id')
    if not user_id or user_id not in (race.editors_allowed or []):
        flash("У вас нет прав на редактирование этой расы.", "danger")
        return redirect(url_for('races.view_race', race_id=race.id))

    form = RaceForm(obj=race)
    abilities = RaceAbility.query.filter_by(race_id=race.id).all()
    existing_abilities = [
        {'id': ab.id, 'name': ab.name, 'description': ab.description}
        for ab in abilities
    ]

    if form.validate_on_submit():
        try:
            abilities_data = json.loads(form.abilities_json_field.data or "[]")
        except json.JSONDecodeError:
            flash('Ошибка в формате данных умений.', 'danger')
            return render_template('create_edit_race.html.jinja', form=form, mode='edit', existing_abilities_json=json.dumps(existing_abilities))

        race.name = form.name.data
        race.description = form.description.data
        race.image_url = form.image_url.data

        # Удаляем старые умения и добавляем новые
        RaceAbility.query.filter_by(race_id=race.id).delete()
        for ability_data in abilities_data:
            ability = RaceAbility(
                race_id=race.id,
                name=ability_data.get('name', ''),
                description=ability_data.get('description', '')
            )
            db.session.add(ability)
        db.session.commit()
        flash('Раса успешно обновлена!', 'success')
        return redirect(url_for('races.view_race', race_id=race.id))

    return render_template(
        'create_edit_race.html.jinja',
        form=form,
        mode='edit',
        race_id=race.id,
        existing_abilities_json=json.dumps(existing_abilities)
    )
