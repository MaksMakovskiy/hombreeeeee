from functools import wraps
from flask import session, redirect, url_for, flash, abort, request
from crud import is_allowed_to_edit, Class, Subclass

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему, чтобы получить доступ к этой странице.', 'info')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def editor_required(f):
    @wraps(f)
    def decorated_function(class_id, *args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            flash('Вы не авторизованы.', 'danger')
            return redirect(url_for('auth.login'))

        content_type = request.path.split('/')[1]
        if content_type == 'classes':
            content_object = Class.query.get_or_404(class_id)
        elif content_type == 'subclasses':
            content_object = Subclass.query.get_or_404(class_id)
        else:
            abort(404)

        if not is_allowed_to_edit(user_id, content_object):
            flash('У вас нет прав на редактирование этого контента.', 'danger')
            abort(403)
        return f(class_id, *args, **kwargs)
    return decorated_function
