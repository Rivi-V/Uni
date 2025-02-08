# Для определения типа данных столбцов
from datetime import datetime, timezone
from typing import Optional
from werkzeug.security import generate_password_hash, check_password_hash

import sqlalchemy as sa
import sqlalchemy.orm as so

# Для наследования
from flask_login import UserMixin

from app import db
from app import login


from random import randint


followers = sa.Table( # ассоциативная таблица многие ко многим
    'followers', # имя таблицы
    db.metadata, # методанные, где SQL хранит всю информацию о таблицах
    sa.Column('follower_id', sa.Integer, sa.ForeignKey('user.id'), # столбец именя, тип и параметры
              primary_key=True),
    sa.Column('followed_id', sa.Integer, sa.ForeignKey('user.id'),
              primary_key=True)
)

class Role(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(64), unique=True, nullable=False)
    description: so.Mapped[Optional[str]] = so.mapped_column(sa.String(255))

    def __repr__(self):
        return f'<Role {self.name}>'

class User(UserMixin, db.Model):
  id: so.Mapped[int] = so.mapped_column(primary_key=True)
  username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
  email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
  password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
  about_me: so.Mapped[Optional[str]] = so.mapped_column(sa.String(140))
  avatar: so.Mapped[str] = so.mapped_column(sa.String(3), default=lambda: str(randint(1, 5))) 
  role: so.Mapped[Optional[str]] = so.mapped_column(sa.String(120))
   
  last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc))

  posts: so.WriteOnlyMapped['Post'] = so.relationship(back_populates='author')

  following: so.WriteOnlyMapped['User'] = so.relationship(
        secondary=followers, # настраивает таблицу ассоциаций, которая используется для этой связи.
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id), # пользователь подписан на -> кого-то  
        back_populates='followers') # с кем связан
  followers: so.WriteOnlyMapped['User'] = so.relationship(
        secondary=followers, 
        primaryjoin=(followers.c.followed_id == id), # на пользователя подписан -> подписчик
        secondaryjoin=(followers.c.follower_id == id),
        back_populates='following')

  def has_role(self, role_name: str) -> bool:
        """Проверяет, имеет ли пользователь указанную роль."""
        return any(role.name == role_name for role in self.roles)
  
  def __repr__(self):
        return '<User {}>'.format(self.username)
  
  def set_password(self, password):
    self.password_hash = generate_password_hash(password)

  def check_password(self, password):
    return check_password_hash(self.password_hash, password)
  
  def is_following(self, user): # подписан ли self на user.
        query = self.following.select().where(User.id == user.id) # ищем user в подписках self
        return db.session.scalar(query) is not None

  def follow(self, user): # если self не подписан на user, то добавляем user в подписки
        if not self.is_following(user):
            self.following.add(user)

  def unfollow(self, user): # если self подписан на user, то удаляем user из подписок
        if self.is_following(user):
            self.following.remove(user)

  def followers_count(self):
        query = sa.select(sa.func.count()).select_from(
            self.followers.select().subquery()) # создаём запрос для подсчёта followers (В этом случае мы подсчитываем количество записей в результате подзапроса)
        return db.session.scalar(query) # выполняет запрос и возвращает единственное число (потому что у запроса метод count)

  def following_count(self):
        query = sa.select(sa.func.count()).select_from(
            self.following.select().subquery())
        return db.session.scalar(query)
  
  def following_posts(self):
        Author = so.aliased(User) # Создаем псевдонимы для User 
        Follower = so.aliased(User)
        return (
            sa.select(Post) # Выбираем все посты
            .join(Post.author.of_type(Author)) # Присоединяем таблицу User как авторов постов
            .join(Author.followers.of_type(Follower), isouter=True) # Присоединяем подписчиков авторов
            # (isouter - Возвращает все записи из левой таблицы (в нашем случае — авторы постов), даже если в правой таблице (подписчики) нет соответствий.)
            .where(sa.or_( # Фильтруем посты или то, или это надо
                Follower.id == self.id,  # Посты от пользователей, на которых подписан текущий пользователь
                Author.id == self.id,  # Собственные посты текущего пользователя
            ))
            .group_by(Post) # Группируем результаты по постам (для избежания дубликатов)
            .order_by(Post.timestamp.desc()) # Сортируем посты по времени создания (новые сначала)
        )


class Post(db.Model):
  id: so.Mapped[int] = so.mapped_column(primary_key=True)
  body: so.Mapped[str] = so.mapped_column(sa.String(10000))
  timestamp: so.Mapped[datetime] = so.mapped_column(index=True, default=lambda: datetime.now(timezone.utc))
  user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)

  author: so.Mapped['User'] = so.relationship(back_populates='posts')

  def __repr__(self):
    return '<Post {}>'.format(self.body)
  
@login.user_loader
def load_user(id):
  return db.session.get(User, int(id)) # id — это строковое представление идентификатора пользователя, которое хранится в сессии -> current_user или AnonymousUserMixin
