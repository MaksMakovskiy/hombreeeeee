from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField, StringField
from wtforms.validators import DataRequired, Length, Optional

class CommentForm(FlaskForm):
    text = TextAreaField('', validators=[DataRequired(), Length(min=5, max=500)])
    submit = SubmitField('Добавить комментарий')

class ProfileForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=3, max=20)])
    submit = SubmitField('Обновить профиль')
