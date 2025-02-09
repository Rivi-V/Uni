"# Uni"

Для того, чтобы найти юзера в flask shell
from app.models import User
user = User.query.filter_by(name='Vika').first()

users = User.query.all()
for user in users:
     print(user.role)

db.session.commit()