from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length

class CommentForm(FlaskForm):
    text = TextAreaField('', validators=[DataRequired(), Length(min=5, max=500)])
    submit = SubmitField('Добавить комментарий')
