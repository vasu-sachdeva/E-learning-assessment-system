from flask import Flask, render_template, request, redirect, url_for, jsonify, flash,session, redirect
from flask_session import Session
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, DateTimeField, BooleanField, IntegerField, DecimalField, HiddenField, SelectField, RadioField
from flask_wtf import FlaskForm
from functools import wraps
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

def user_role_professor(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            if session['user_role'] == "teacher":
                return f(*args, **kwargs)
            else:
                flash('You dont have privilege to access this page!','danger')
                return render_template("404.html")
        else:
            flash('Unauthorized, Please login!','danger')
            return redirect(url_for('login'))
    return wrap

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
	return render_template('index.html', messages = 'My name is proctor')

@app.route('/login', methods=['GET','POST'])
def login():
	if request.method == 'POST':
		email = request.form['email']
		password_candidate = request.form['password']
		user_type = request.form['user_type']
		imgdata1 = request.form['image_hidden']
		cur = mysql.connection.cursor()
		results1 = cur.execute('SELECT uid, name, email, password, user_type, user_image from users where email = %s and user_type = %s and user_login = 0' , (email,user_type))
		if results1 > 0:
			cresults = cur.fetchone()
			imgdata2 = cresults['user_image']
			password = cresults['password']
			name = cresults['name']
			uid = cresults['uid']
			nparr1 = np.frombuffer(base64.b64decode(imgdata1), np.uint8)
			nparr2 = np.frombuffer(base64.b64decode(imgdata2), np.uint8)
			image1 = cv2.imdecode(nparr1, cv2.COLOR_BGR2GRAY)
			image2 = cv2.imdecode(nparr2, cv2.COLOR_BGR2GRAY)
			img_result  = DeepFace.verify(image1, image2, enforce_detection = False)
			if img_result["verified"] == True and password == password_candidate:
				results2 = cur.execute('UPDATE users set user_login = 1 where email = %s' , [email])
				mysql.connection.commit()
				if results2 > 0:
					session['logged_in'] = True
					session['email'] = email
					session['name'] = name
					session['user_role'] = user_type
					session['uid'] = uid
					if user_type == "student":
						return redirect(url_for('student_index'))
					else:
						return redirect(url_for('professor_index'))
				else:
					error = 'Error Occurred!'
					return render_template('login.html', error=error)	
			else:
				error = 'Either Image not Verified or you have entered Invalid password or Already login'
				return render_template('login.html', error=error)
			cur.close()
		else:
			error = 'Already Login or Email was not found!'
			return render_template('login.html', error=error)
	return render_template('login.html')

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

@app.route('/deltidlist', methods=['GET'])
@user_role_professor
def deltidlist():
	cur = mysql.connection.cursor()
	results = cur.execute('SELECT * from teachers where email = %s and uid = %s', (session['email'], session['uid']))
	if results > 0:
		cresults = cur.fetchall()
		now = datetime.now()
		now = now.strftime("%Y-%m-%d %H:%M:%S")
		now = datetime.strptime(now,"%Y-%m-%d %H:%M:%S")
		testids = []
		for a in cresults:
			if datetime.strptime(str(a['start']),"%Y-%m-%d %H:%M:%S") > now:
				testids.append(a['test_id'])
		cur.close()
		return render_template("deltidlist.html", cresults = testids)
	else:
		return render_template("deltidlist.html", cresults = None)

@app.route('/deldispques', methods=['GET','POST'])
@user_role_professor
def deldispques():
	if request.method == 'POST':
		tidoption = request.form['choosetid']
		et = examtypecheck(tidoption)
		if et['test_type'] == "objective":
			cur = mysql.connection.cursor()
			cur.execute('SELECT * from questions where test_id = %s and uid = %s', (tidoption,session['uid']))
			callresults = cur.fetchall()
			cur.close()
			return render_template("deldispques.html", callresults = callresults, tid = tidoption)
		elif et['test_type'] == "subjective":
			cur = mysql.connection.cursor()
			cur.execute('SELECT * from longqa where test_id = %s and uid = %s', (tidoption,session['uid']))
			callresults = cur.fetchall()
			cur.close()
			return render_template("deldispquesLQA.html", callresults = callresults, tid = tidoption)
		elif et['test_type'] == "practical":
			cur = mysql.connection.cursor()
			cur.execute('SELECT * from practicalqa where test_id = %s and uid = %s', (tidoption,session['uid']))
			callresults = cur.fetchall()
			cur.close()
			return render_template("deldispquesPQA.html", callresults = callresults, tid = tidoption)
		else:
			flash("Some Error Occured!")
			return redirect(url_for('/deltidlist'))
if __name__ == "__main__":
	app.run()
