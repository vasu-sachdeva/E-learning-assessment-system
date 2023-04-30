from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, DateTimeField, BooleanField, IntegerField, DecimalField, HiddenField, SelectField, RadioField
from flask_wtf import FlaskForm
from wtforms.fields import DateField, TimeField
from datetime import timedelta, datetime
from wtforms.validators import ValidationError, NumberRange,InputRequired,Length
from flask_wtf.file import FileField, FileRequired, file_allowed
from coolname import generate_slug
import pandas as pd
from objective import ObjectiveTest

app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'quizapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

app.secret_key = 'cvproject'
mysql = MySQL(app)

class UploadForm(FlaskForm):
	subject = StringField('Subject',validators=[InputRequired(message="required")])
	topic = StringField('Topic')
	# doc = FileField('CSV Upload', validators=[FileRequired()])
	start_date = DateField('Start Date')
	start_time = TimeField('Start Time', default=datetime.utcnow()+timedelta(hours=5.5))
	end_date = DateField('End Date')
	end_time = TimeField('End Time', default=datetime.utcnow()+timedelta(hours=5.5))
	calc = BooleanField('Enable Calculator')
	neg_mark = DecimalField('Enable negative marking in % ', validators=[NumberRange(min=0, max=100)])
	duration = IntegerField('Duration(in min)')
	password = PasswordField('Exam Password', [Length(min=3, max=6, message="short password")])

	def validate_end_date(form, field):
		if field.data < form.start_date.data:
			raise ValidationError("End date must not be earlier than start date.")
	
	def validate_end_time(form, field):
		start_date_time = datetime.strptime(str(form.start_date.data) + " " + str(form.start_time.data),"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
		end_date_time = datetime.strptime(str(form.end_date.data) + " " + str(field.data),"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
		if start_date_time >= end_date_time:
			raise ValidationError("End date time must not be earlier/equal than start date time")
	
	def validate_start_date(form, field):
		if datetime.strptime(str(form.start_date.data) + " " + str(form.start_time.data),"%Y-%m-%d %H:%M:%S") < datetime.now():
			raise ValidationError("Start date and time must not be earlier than current")

@app.route("/")
def index():
	return render_template('index.html', messages = 'My name is Khan')

@app.route("/professor_index")
def professor_index():
	return render_template('professor_index.html')

@app.route("/create-test", methods = ['GET', 'POST'])
def create_test():
	form = UploadForm()
	if request.method=='POST' and form.validate_on_submit():
		# print(form.errors)
		test_id = generate_slug(2)
		# filename = secure_filename(form.doc.data.filename)
		# filestream = form.doc.data
		# filestream.seek(0)
		# ef = pd.read_csv(filestream)
		# fields = ['qid','q','marks']
		# df = pd.DataFrame(ef, columns = fields)
		# cur = mysql.connection.cursor()
		# for row in df.index:
		# 	cur.execute('INSERT INTO questions(test_id,qid,q,a,b,c,d,ans,marks,uid) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', (test_id, df['qid'][row], df['q'][row], df['a'][row], df['b'][row], df['c'][row], df['d'][row], df['ans'][row], df['marks'][row], session['uid']))
		# 	cur.connection.commit()
		start_date = form.start_date.data
		end_date = form.end_date.data
		start_time = form.start_time.data
		end_time = form.end_time.data
		start_date_time = str(start_date) + " " + str(start_time)
		end_date_time = str(end_date) + " " + str(end_time)
		neg_mark = int(form.neg_mark.data)
		calc = int(form.calc.data)
		duration = int(form.duration.data)*60
		password = form.password.data
		subject = form.subject.data
		topic = form.topic.data
		# print(form.subject.errors)
		# proctor_type = form.proctor_type.data
		print(start_date, end_date, start_time, end_time, start_date_time, end_date_time, neg_mark, calc, duration, password, subject, topic)
		
		# Here queries of database will bew written #
		# cur.close()
		flash(f'Exam ID: {test_id}', 'success')
		return redirect(url_for('professor_index'))
	return render_template('create_test.html', form = form)

@app.route('/generate_test')
def generate_test():
	return render_template('generate_test.html')

@app.route('/test_generate', methods=["GET", "POST"])
def test_generate():
	if request.method == "POST":
		inputText = request.form["itext"]
		testType = request.form["test_type"]
		noOfQues = request.form["noq"]
		if testType == "objective":
			objective_generator = ObjectiveTest(inputText,noOfQues)
			question_list, answer_list = objective_generator.generate_test()
			testgenerate = zip(question_list, answer_list)
			return render_template('generatedtestdata.html', cresults = testgenerate)
		else:
			return None

if __name__ == "__main__":
	app.run()
