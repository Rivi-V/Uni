import os
from urllib.parse import urlsplit

from flask import render_template, flash, redirect, url_for, request, send_from_directory
from flask_login import login_user, logout_user, current_user, login_required

import sqlalchemy as sa

from app import app, db
from app.forms import LoginForm, RegistrationForm,  EditProfileForm, EmptyForm, PostForm, GBTForm, Search
from app.models import User, Post, followers

from datetime import datetime, timezone

from g4f.client import Client

import markdown
from bleach import clean

number = 0

@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()
        
       
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Вы зарегистрировались!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Неверное имя пользователя или пароль.')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data) # сохраняет id юзера в системе
        next_page = request.args.get('next') # на какую страницу хотел попасть неавторизованный пользователь
        if not next_page or urlsplit(next_page).netloc != '': # если next_page None или на внешний сайт переход (netloc - сетевое расположение)
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Вход', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/edit_profile/<username>', methods=['GET', 'POST'])
@login_required
def edit_profile(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    form = EditProfileForm(user.username)
    global number
    if form.validate_on_submit():
        if form.submit.data:
            user.username = form.username.data
            user.about_me = form.about_me.data
            user.avatar = str(number + int(user.avatar))
            db.session.commit()
            number = 0
            flash('Изменения сохранены.')
            return redirect(url_for('edit_profile'))
        if form.avatar.data:  
            number = number + 1 if (number + int(user.avatar)) < 5 else -1 * int(user.avatar) + 1
    elif request.method == 'GET':
        form.username.data = user.username # чтобы в форме были данные, которые у вас сейчас в бд
        form.about_me.data = user.about_me
    return render_template('edit_profile.html', title='Изменить профиль',
                           form=form, number=number+int(user.avatar))

 
@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    form_gbt = GBTForm()

    if form.validate_on_submit():
        post = Post(body=markdown.markdown(form.post.data), author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Твой пост опубликован!')
        return redirect(url_for('index'))
    
    page = request.args.get('page', 1, type=int) # Здесь мы получаем параметр page из URL-запроса (например, /index?page=2 (иначе 1)).
    posts = db.paginate(current_user.following_posts(), page=page, # page: Номер страницы, которую нужно показать.
                        per_page=app.config['POSTS_PER_PAGE'], error_out=False) 
    next_url = url_for('index', page=posts.next_num) \
        if posts.has_next else None # след страница (если есть)
    prev_url = url_for('index', page=posts.prev_num) \
        if posts.has_prev else None # предыдущая страница (если есть)

    if form_gbt.validate_on_submit():
        question = form_gbt.question.data
        flash('Твой вопрос отправлен!')
        client = Client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": question + "В ответе не используй # и формулы, формотирование"}],
            web_search=False,
            use_chat_history=False
        )
        generated_text = response.choices[0].message.content.strip()  
        if "<!DOCTYPE HTML" in generated_text:
            form.post.data = "Ошибка! Непредвиденный HTML тэг."
        else: 
            form.post.data = generated_text

    return render_template(
        'index.html',
        title='Стена',
        form=form,
        posts=posts.items,
        next_url=next_url,
        prev_url=prev_url,
        form_gbt=form_gbt
    )


@app.route('/followers/<username>', methods=['GET', 'POST'])
@login_required
def followers(username):
    page = request.args.get('page', 1, type=int)
    
    # Получаем запрос на подписчиков
    query = current_user.all_followers()

    all_followers = db.paginate(
        query,
        page=page,
        per_page=app.config['POSTS_PER_PAGE'],
        error_out=False
    )

    next_url = url_for('followers', username=username, page=all_followers.next_num) \
        if all_followers.has_next else None
    prev_url = url_for('followers', username=username, page=all_followers.prev_num) \
        if all_followers.has_prev else None

    return render_template(
        'followers.html',
        title='Стена',
        followers=all_followers.items,
        next_url=next_url,
        prev_url=prev_url,
    )

@app.route('/followed/<username>', methods=['GET', 'POST'])
@login_required
def followed(username):
    page = request.args.get('page', 1, type=int)
    query = current_user.all_followed()

    # Применяем пагинацию
    all_followed = db.paginate(
        query,
        page=page,
        per_page=app.config['POSTS_PER_PAGE'],
        error_out=False
    )

    next_url = url_for('followers', username=username, page=all_followed.next_num) \
        if all_followed.has_next else None
    prev_url = url_for('followers', username=username, page=all_followed.prev_num) \
        if all_followed.has_prev else None

    return render_template(
        'followers.html',
        title='Стена',
        followers=all_followed.items,
        next_url=next_url,
        prev_url=prev_url,
    )


@app.route('/user/<username>') # динамический компонент URL <>
@login_required
def user(username): # передаёт из URL
    user = db.first_or_404(sa.select(User).where(User.username == username))
    page = request.args.get('page', 1, type=int)
    query = sa.select(Post).where(Post.user_id == user.id).order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page,
                        per_page=app.config['POSTS_PER_PAGE'],
                        error_out=False)
    next_url = url_for('user', username=user.username, page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('user', username=user.username, page=posts.prev_num) \
        if posts.has_prev else None
    form = EmptyForm()
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url, form=form)


@app.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(f'Пользоватьель {username} не найден.')
            return redirect(url_for('index'))
        if user == current_user:
            flash('Вы не можете подписаться на себя!')
            return redirect(url_for('user', username=username))
        current_user.follow(user)
        db.session.commit()
        flash(f'Вы подписались на {username}!')
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))


@app.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(f'Пользователь {username} не найден.')
            return redirect(url_for('index'))
        if user == current_user:
            flash('Вы не можете отписаться от себя!')
            return redirect(url_for('user', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(f'Вы отписались от {username}.')
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))
    

@app.route('/explore', methods=['GET', 'POST'])
@login_required
def explore():
    form = Search()  
    if form.validate_on_submit(): 
        user = db.session.scalar(
            sa.select(User).where(User.username == form.query.data))
        if user is None:
            flash('Пользователь не найден.')
            query = sa.select(Post).order_by(Post.timestamp.desc())
        else:
            flash('Пользователь найден.')
            query = sa.select(Post).where(Post.user_id == user.id).order_by(Post.timestamp.desc())
    else: 
            query = sa.select(Post).order_by(Post.timestamp.desc())
    
    
    page = request.args.get('page', 1, type=int)
    posts = db.paginate(query, page=page,
                        per_page=app.config['POSTS_PER_PAGE'], error_out=False)
    
    if not posts.items:
            return redirect(url_for('user', username=user.username))

    next_url = url_for('explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('explore', page=posts.prev_num) \
        if posts.has_prev else None

    return render_template("explore.html", title='Все посты', posts=posts.items,
                           next_url=next_url, prev_url=prev_url, form=form)


@app.route('/delete/<username>/<post_id>/<time>', methods=['POST'])
@login_required
def delete(username, post_id, time):
    form = EmptyForm()
    if form.validate_on_submit():

        post_to_delete = db.session.query(Post).filter_by(id=post_id, timestamp=time).first()

        if not post_to_delete:
            flash(f'Сообщение не найдено.')
            return redirect(url_for('user', username=username))
        
        db.session.delete(post_to_delete)
        db.session.commit()

        return redirect(url_for('user', username=username))
    
    return redirect(url_for('index'))
    
@app.route('/about')
def about():
    return render_template("about_us.html")

@app.route('/avatar/<number>')
def avatar(number):
    number += '.png'
    avatar_dir = os.path.join(app.config['UPLOAD_FOLDER'], "avatar")
    return send_from_directory(avatar_dir, number, max_age=3600)


@app.route('/image/<name>')
def image(name):
    return send_from_directory(app.config['UPLOAD_FOLDER'], name)

