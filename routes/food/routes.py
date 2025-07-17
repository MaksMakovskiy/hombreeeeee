from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired
from crud import db, Food, User, Comment
from utils.decorators import login_required
from forms.comments import CommentForm
import json

food_bp = Blueprint('food', __name__, url_prefix='/food')

class FoodForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    description = TextAreaField('Описание', validators=[DataRequired()])
    image_url = StringField('URL картинки')
    submit = SubmitField('Сохранить')

@food_bp.route("/")
def list_food():
    foods = Food.query.all()
    return render_template('list_food.html.jinja', foods=foods)

@food_bp.route("/create", methods=['GET', 'POST'])
@login_required
def create_food():
    form = FoodForm()
    if form.validate_on_submit():
        new_food = Food(
            name=form.name.data,
            description=form.description.data,
            image_url=form.image_url.data,
            user_id=session['user_id'],
            editors_allowed=[session['user_id']]
        )
        db.session.add(new_food)
        db.session.commit()
        flash('Еда успешно создана!', 'success')
        return redirect(url_for('food.view_food', food_id=new_food.id))
    return render_template('create_edit_food.html.jinja', form=form, mode='create')

@food_bp.route("/<int:food_id>")
def view_food(food_id):
    food = Food.query.get_or_404(food_id)
    can_edit = session.get('user_id') in (food.editors_allowed or [])
    comment_form = CommentForm()
    comments = Comment.query.filter_by(food_id=food_id).order_by(Comment.timestamp.asc()).all()
    
    # Получаем текущего пользователя для проверки в шаблоне
    user = None
    if session.get('user_id'):
        user = User.query.get(session['user_id'])
    
    return render_template(
        'view_food.html.jinja',
        food=food,
        can_edit=can_edit,
        comment_form=comment_form,
        comments=comments,
        user=user
    )

@food_bp.route("/<int:food_id>/edit", methods=['GET', 'POST'])
@login_required
def edit_food(food_id):
    food = Food.query.get_or_404(food_id)
    user_id = session.get('user_id')
    if not user_id or user_id not in (food.editors_allowed or []):
        flash("У вас нет прав на редактирование этой еды.", "danger")
        return redirect(url_for('food.view_food', food_id=food.id))

    form = FoodForm(obj=food)
    if form.validate_on_submit():
        food.name = form.name.data
        food.description = form.description.data
        food.image_url = form.image_url.data
        db.session.commit()
        flash('Еда успешно обновлена!', 'success')
        return redirect(url_for('food.view_food', food_id=food.id))

    return render_template('create_edit_food.html.jinja', form=form, mode='edit', food_id=food.id)

@food_bp.route("/grant_edit/<int:food_id>", methods=['GET', 'POST'])
@login_required
def grant_edit_food(food_id):
    food = Food.query.get_or_404(food_id)
    if request.method == "POST":
        username = request.form.get("username")
        user = User.query.filter_by(username=username).first()
        if not user:
            flash("Пользователь не найден.", "danger")
        else:
            if user.id not in (food.editors_allowed or []):
                food.editors_allowed.append(user.id)
                db.session.commit()
            flash(f"Права на редактирование выданы пользователю {username}.", "success")
        return redirect(request.url)
    return render_template("grant_edit_food.html.jinja", food=food)

@food_bp.route("/<int:food_id>/comment", methods=['POST'])
@login_required
def add_comment(food_id):
    form = CommentForm()
    if form.validate_on_submit():
        user_id = session['user_id']
        comment = Comment(
            user_id=user_id,
            text=form.text.data,
            food_id=food_id
        )
        db.session.add(comment)
        db.session.commit()
        flash('Комментарий добавлен!', 'success')
    else:
        flash('Ошибка при добавлении комментария.', 'danger')
    return redirect(url_for('food.view_food', food_id=food_id))

@food_bp.route("/<int:food_id>/delete", methods=['GET', 'POST'])
@login_required
def delete_food(food_id):
    food = Food.query.get_or_404(food_id)
    
    # Проверяем права: только автор может удалить еду
    if session['user_id'] != food.user_id:
        flash('У вас нет прав для удаления этой еды.', 'danger')
        return redirect(url_for('food.view_food', food_id=food_id))
    
    # CASCADE на связях Food поможет удалить Comments
    db.session.delete(food)
    db.session.commit()
    flash('Еда успешно удалена!', 'success')
    return redirect(url_for('food.list_food'))
