from flask import Blueprint, render_template, redirect, url_for, flash, g, request
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length
from crud import db, Article, Comment, User
from utils.decorators import login_required
from forms.comments import CommentForm
import json

articles_bp = Blueprint('articles', __name__, url_prefix='/articles')

class ArticleForm(FlaskForm):
    title = StringField('Название статьи', validators=[DataRequired(), Length(min=3, max=200)])
    content = TextAreaField('Содержание', validators=[DataRequired(), Length(min=10)])
    submit = SubmitField('Сохранить статью')

@articles_bp.route("/")
def list_articles():
    """Список всех статей"""
    articles = Article.query.order_by(Article.created_at.desc()).all()
    return render_template('list_articles.html.jinja', articles=articles)

@articles_bp.route("/create", methods=['GET', 'POST'])
@login_required
def create_article():
    """Создание новой статьи"""
    form = ArticleForm()
    if form.validate_on_submit():
        article = Article(
            title=form.title.data,
            content=form.content.data,
            user_id=g.user.id
        )
        db.session.add(article)
        db.session.commit()
        flash('Статья успешно создана!', 'success')
        return redirect(url_for('articles.view_article', article_id=article.id))
    
    return render_template('create_edit_article.html.jinja', form=form, action="Создание")

@articles_bp.route("/<int:article_id>")
def view_article(article_id):
    """Просмотр статьи"""
    article = Article.query.get_or_404(article_id)
    comments = Comment.query.filter_by(article_id=article_id).order_by(Comment.timestamp.desc()).all()
    comment_form = CommentForm()
    
    return render_template('view_article.html.jinja', 
                         article=article, 
                         comments=comments, 
                         comment_form=comment_form)

@articles_bp.route("/<int:article_id>/edit", methods=['GET', 'POST'])
@login_required
def edit_article(article_id):
    """Редактирование статьи"""
    article = Article.query.get_or_404(article_id)
    
    # Проверяем права доступа
    if article.user_id != g.user.id and g.user.id not in (article.editors_allowed or []):
        flash('У вас нет прав для редактирования этой статьи.', 'danger')
        return redirect(url_for('articles.view_article', article_id=article_id))
    
    form = ArticleForm(obj=article)
    if form.validate_on_submit():
        article.title = form.title.data
        article.content = form.content.data
        db.session.commit()
        flash('Статья успешно обновлена!', 'success')
        return redirect(url_for('articles.view_article', article_id=article_id))
    
    return render_template('create_edit_article.html.jinja', 
                         form=form, 
                         action="Редактирование", 
                         article=article)

@articles_bp.route("/<int:article_id>/delete", methods=['POST'])
@login_required
def delete_article(article_id):
    """Удаление статьи"""
    article = Article.query.get_or_404(article_id)
    
    # Проверяем права доступа
    if article.user_id != g.user.id:
        flash('У вас нет прав для удаления этой статьи.', 'danger')
        return redirect(url_for('articles.view_article', article_id=article_id))
    
    db.session.delete(article)
    db.session.commit()
    flash('Статья успешно удалена!', 'success')
    return redirect(url_for('articles.list_articles'))

@articles_bp.route("/<int:article_id>/comment", methods=['POST'])
@login_required
def add_comment(article_id):
    """Добавление комментария к статье"""
    article = Article.query.get_or_404(article_id)
    form = CommentForm()
    
    if form.validate_on_submit():
        comment = Comment(
            text=form.text.data,
            user_id=g.user.id,
            article_id=article_id
        )
        db.session.add(comment)
        db.session.commit()
        flash('Комментарий добавлен!', 'success')
    else:
        for error in form.text.errors:
            flash(error, 'danger')
    
    return redirect(url_for('articles.view_article', article_id=article_id))
