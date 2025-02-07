# Data Base
import sqlalchemy as sa
from app import db

# Forms
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Length

from app.models import User

class EmptyForm(FlaskForm):
    submit = SubmitField('')

    
class Search(FlaskForm):
    query = TextAreaField('Поиск', validators=[Length(min=1, max=10000)])
    submit = SubmitField('Найти') 

class GBTForm(FlaskForm):
    question = TextAreaField('Или попроси помощи у Uni!', validators=[
        DataRequired(), Length(min=1, max=10000)])
    submit = SubmitField('Спросить') 

class LoginForm(FlaskForm):
    username = StringField('Ваше имя', validators=[DataRequired()]) # для регистрации необходимо наличие какой-либо инф.
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить пароль')
    submit = SubmitField('Войти')


class RegistrationForm(FlaskForm):
    username = StringField('Ваше имя', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password2 = PasswordField(
        'Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Регистрация')

    def validate_username(self, usern_name):
        user = db.session.scalar(sa.select(User).where( # за сессию SQLAlchemy, через которую выполняются операции с базой данных, выбираем 1-ую строку, где...
            User.username == usern_name.data)) # usern_name - строка бд, usern_name.data - информация из строки
        if user is not None:
            raise ValidationError('Этот имя занято, пожалуйста, используйте другое.')

    def validate_email(self, usern_email):
        user = db.session.scalar(sa.select(User).where(
            User.email == usern_email.data))
        if user is not None:
            raise ValidationError('Этот email занят, пожалуйста, используйте другой.')
        
class EditProfileForm(FlaskForm):
    username = StringField('Пользователь', validators=[DataRequired()])
    about_me = TextAreaField('Обо мне', validators=[Length(min=0, max=140)])
    avatar = SubmitField('Дальше')
    submit = SubmitField('Подтвердить')

    def __init__(self, original_username, *args, **kwargs): # инициализация оригинального имени
        super().__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username: # если имя старое и новое не совпадают
            user = db.session.scalar(sa.select(User).where( # существует ли пользователь с таким же именем
                User.username == self.username.data))
            if user is not None:
                raise ValidationError('Пожалйста, используйте другое имя!')

class PostForm(FlaskForm):
    post = TextAreaField('Скажи что-нибудь!', validators=[
        DataRequired(), Length(min=1, max=10000)])
    submit = SubmitField('Отправить')
