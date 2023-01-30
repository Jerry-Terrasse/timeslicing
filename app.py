from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy as sa
import pymysql
pymysql.install_as_MySQLdb()
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import wtforms

import os
import sys
import json
from datetime import datetime
import hashlib
from loguru import logger
from typing import Union

db_pass = os.getenv('PASS')
assert db_pass

app = Flask(__name__)
app.secret_key = hashlib.md5(db_pass.encode('utf-8')).hexdigest()

login_manager = LoginManager(app)
login_manager.login_view = 'login'

class Config(object):
    """配置参数"""
    # 设置连接数据库的URL
    user = 'root'
    password = db_pass
    assert password
    database = 'timeslicing'
    SQLALCHEMY_DATABASE_URI = f'mysql://{user}:{password}@127.0.0.1:3306/{database}'

    # 设置sqlalchemy自动更跟踪数据库
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    # 查询时会显示原始SQL语句
    SQLALCHEMY_ECHO = True

    # 禁止自动提交数据处理
    SQLALCHEMY_COMMIT_ON_TEARDOWN = False

app.config.from_object(Config)

db = SQLAlchemy(app)

class Slice(db.Model):
	"""时间片"""
	__tablename__ = 'slices'

	slice_id = sa.Column(sa.Integer, primary_key=True, autoincrement=True, nullable=False, comment='时间片编号')
	user_id = sa.Column(sa.Integer, sa.ForeignKey('users.user_id'), nullable=False, comment='时间片所属用户编号')
	time = sa.Column(sa.DateTime, nullable=False, comment='时间片所在时间起始时间戳')
	affair = sa.Column(sa.Unicode(64), nullable=False, comment='时间片对应事务名称')
	update_time = sa.Column(sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), comment='时间片更新时间戳')

	def __repr__(self):
		return f'<Slice {self.slice_id} {self.time} {self.affair}>'
	
	def simplify(self):
		return [
			int(self.time.timestamp() * 1000),
			self.affair,
			int(self.update_time.timestamp() * 1000)
		]

class User(db.Model, UserMixin):
	"""用户"""
	__tablename__ = 'users'

	user_id = sa.Column(sa.Integer, primary_key=True, autoincrement=True, nullable=False, comment='用户编号') # note: start value is set in init()
	username = sa.Column(sa.Unicode(16), nullable=False, comment='用户名')
	password = sa.Column(sa.Unicode(32), nullable=False, comment='用户密码加盐哈希')

	def __init__(self):
		super().__init__()

	def __repr__(self):
		return f'<User {self.user_id} {self.username}>'
	
	def verify(self, password: str) -> bool:
		return self.password == calc_password(self.username, password)
	
	def get_id(self) -> int:
		return self.user_id
	
	@staticmethod
	@login_manager.user_loader
	def get_by_id(user_id: int) -> Union['User', None]:
		res: sa.engine.Result = db.session.execute(sa.select(User).where(User.user_id == user_id))
		return res.scalar() # return None if not found
	
	@staticmethod
	def get_by_name(username: str) -> Union['User', None]:
		res: sa.engine.Result = db.session.execute(sa.select(User).where(User.username == username))
		return res.scalar() # return None if not found


class LoginForm(wtforms.Form):
	"""登录表单"""
	username = wtforms.StringField('用户名', validators=[wtforms.validators.DataRequired()])
	password = wtforms.PasswordField('密码', validators=[wtforms.validators.DataRequired()])


@app.route('/')
def home():
	return render_template('home.jinja', title='Home', user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	form = LoginForm(request.form)
	error_msg = None
	if request.method == 'POST' and form.validate():
		username = form.username.data
		password = form.password.data
		user = User.get_by_name(username)
		logger.debug(user)
		if user:
			if user.verify(password):
				login_user(user)
				return redirect(url_for('home'))
			else:
				error_msg = '密码错误'
		else:
			error_msg = '用户不存在'
	return render_template('login.jinja', title='Login', user=current_user, form=form, error_msg=error_msg)

@app.route('/logout')
@login_required
def logout():
	logout_user()
	return redirect(url_for('home'))

@app.route('/insert')
@login_required
def insert():
	return render_template('insert.jinja', title='Insert', user=current_user)

@app.post('/insert_post')
@login_required
def submit():
	try:
		logs_str = request.form['logs']
		logs: list[list] = json.loads(logs_str)
		slices = [Slice(user_id=current_user.user_id, time=datetime.fromtimestamp(ts/1000), affair=affair) for ts, affair in logs]
		db.session.add_all(slices)
		db.session.commit()
		return {
			'status': 'success',
			'msg': '插入成功'
		}
	except Exception as e:
		logger.warning(e)
		return {
			'status': 'error',
			'msg': str(e)
		}

@app.route('/inspect')
@login_required
def inspect():
	return render_template('inspect.jinja', title='Inspect', user=current_user)

@app.route('/statistic')
@login_required
def statistic():
	return render_template('statistic.jinja', title='statistic', user=current_user)

@app.get('/query')
@login_required
def query():
	try:
		slices: sa.engine.ScalarResult = db.session.execute(
			sa.select(Slice)
			.where(Slice.user_id == current_user.user_id)
			.order_by(Slice.time)
		).scalars()
		logger.debug(slices)
		# slices: list[Slice] = Slice.query.all()
		return {
			'status': 'success',
			'msg': '查询成功',
			'logs': [slice.simplify() for slice in slices]
		}
	except Exception as e:
		logger.warning(e)
		return {
			'status': 'error',
			'msg': str(e)
		}

def calc_password(username, password):
	return hashlib.md5((password + username).encode('utf-8')).hexdigest()

def init():
	with app.app_context():
		db.drop_all()
		db.create_all()
		db.session.execute(sa.text('ALTER TABLE users AUTO_INCREMENT=10000;'))
		# x=Slice.query.all()
		# print(x)
		# print(x[0].time)
		# print(type(x[0].time))

if __name__ == '__main__':
	if sys.argv.count("init"):
		init()
	if sys.argv.count("register"):
		with app.app_context():
			username = input('username: ')
			password = input('password: ')
			user = User(username=username, password=calc_password(username, password))
			db.session.add(user)
			db.session.commit()