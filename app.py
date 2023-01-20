from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
import pymysql
pymysql.install_as_MySQLdb()

import os
import json
from datetime import datetime

app = Flask(__name__)

class Config(object):
    """配置参数"""
    # 设置连接数据库的URL
    user = 'root'
    password = os.getenv('PASS')
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

	slice_id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False, comment='时间片编号')
	time = db.Column(db.DateTime, nullable=False, comment='时间片所在时间起始时间戳')
	affair = db.Column(db.Unicode(64), nullable=False, comment='时间片对应事务名称')
	update_time = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), comment='时间片更新时间戳')

	def __repr__(self):
		return f'<Slice {self.slice_id} {self.time} {self.affair}>'
	
	def simplify(self):
		return [
			int(self.time.timestamp() * 1000),
			self.affair,
			int(self.update_time.timestamp() * 1000)
		]


@app.route('/')
def home():
	return render_template('home.jinja', title='Home')

@app.route('/insert')
def insert():
	return render_template('insert.jinja')

@app.post('/insert_post')
def submit():
	try:
		logs_str = request.form['logs']
		logs: list[list] = json.loads(logs_str)
		slices = [Slice(time=datetime.fromtimestamp(ts/1000), affair=affair) for ts, affair in logs]
		db.session.add_all(slices)
		db.session.commit()
		return {
			'status': 'success',
			'msg': '插入成功'
		}
	except Exception as e:
		return {
			'status': 'error',
			'msg': str(e)
		}

@app.route('/inspect')
def inspect():
	return render_template('inspect.jinja')

@app.get('/query')
def query():
	try:
		slices: list[Slice] = Slice.query.all()
		return {
			'status': 'success',
			'msg': '查询成功',
			'logs': [slice.simplify() for slice in slices]
		}
	except Exception as e:
		return {
			'status': 'error',
			'msg': str(e)
		}

if __name__ == '__main__':
	with app.app_context():
		db.drop_all()
		db.create_all()
		# x=Slice.query.all()
		# print(x)
		# print(x[0].time)
		# print(type(x[0].time))