from functools import wraps
from typing import Callable, Any

from flask_wtf import FlaskForm
from quart.exceptions import Unauthorized
from quart_auth import current_user, logout_user
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import DataRequired


class LoginForm(FlaskForm):
    email = StringField('email', validators=[DataRequired()])
    password = PasswordField("password", validators=[DataRequired()])
    guest = BooleanField('guest', default=False)


def user_required(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        if current_user and current_user.auth_id == "guest":
            logout_user()
            raise Unauthorized()
        else:
            return await func(*args, **kwargs)

    return wrapper