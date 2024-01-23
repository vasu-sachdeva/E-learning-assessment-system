from ultralytics import YOLO
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash,session, redirect
from flask_mysqldb import MySQL
from flask_mail import Mail, Message
import math, random 
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, DateTimeField, BooleanField, IntegerField, DecimalField, HiddenField, SelectField, RadioField
from flask_wtf import FlaskForm
from functools import wraps
from wtforms.fields import DateField, TimeField
from datetime import timedelta, datetime
from wtforms.validators import ValidationError, NumberRange,InputRequired,Length
from flask_wtf.file import FileField, FileRequired, FileAllowed
from coolname import generate_slug
import pandas as pd
from objective import ObjectiveTest	
import numpy as np
import cv2
import json
import stripe
import base64
from flask_session import Session
from flask_cors import CORS, cross_origin
# import camera
from deepface import DeepFace
# from gaze_tracking.gaze_tracking import GazeTracking

app = Flask(__name__)

app.secret_key= 'sem6project'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'quizapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'


with open('emailConfig.json') as file:
    emailData = json.load(file)


app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = emailData['email']
app.config['MAIL_PASSWORD'] = emailData['password']
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

app.config['SESSION_COOKIE_SAMESITE'] = "None"

app.config['SESSION_TYPE'] = 'filesystem'

app.config["TEMPLATES_AUTO_RELOAD"] = True

stripe_keys = {
	"secret_key": "dummy",
	"publishable_key": "dummy",
}

stripe.api_key = stripe_keys["secret_key"]

mail = Mail(app)

sess = Session()
sess.init_app(app)

app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True

cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

mysql = MySQL(app)

sender = 'youremail@abc.com'

YOUR_DOMAIN = 'http://localhost:5000'

@app.before_request
def make_session_permanent():
	session.permanent = True

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

def user_role_student(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			if session['user_role']=="student":
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
	doc = FileField('CSV Upload', validators=[FileRequired()])
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
	if 'email' in session:
		print(session)
		if session['user_role']=="student":
			return redirect(url_for('student_index'))
		return redirect(url_for('professor_index'))
	return render_template('index.html', messages = 'My name is proctor')

def generateOTP() : 
	digits = "0123456789"
	OTP = "" 
	for i in range(5) : 
		OTP += digits[math.floor(random.random() * 10)] 
	return OTP 

@app.route('/register', methods=['GET','POST'])
def register():
	if request.method == 'POST':
		name = request.form['name']
		email = request.form['email']
		password = request.form['password']
		user_type = request.form['user_type']
		imgdata = request.form['image_hidden']
		session['tempName'] = name
		session['tempEmail'] = email
		session['tempPassword'] = password
		session['tempUT'] = user_type
		session['tempImage'] = imgdata
		sesOTP = generateOTP()
		session['tempOTP'] = sesOTP
		msg1 = Message('E-Learning Assessment System - OTP Verification', sender = sender, recipients = [email])
		msg1.body = "New Account opening - Your OTP Verfication code is "+sesOTP+"."
		mail.send(msg1)
		return redirect(url_for('verifyEmail')) 
	return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
	if request.method == 'POST':
		email = request.form['email']
		password_candidate = request.form['password']
		user_type = request.form['user_type']
		imgdata1 = request.form['image_hidden']
		cur = mysql.connection.cursor()
		results1 = cur.execute('SELECT uid, name, email, password, user_type, user_image from users where email = %s and user_type = %s and user_login = 0' , (email,user_type))
		# results1 = cur.execute('SELECT uid, name, email, password, user_type from users where email = %s and user_type = %s and user_login = 0' , (email,user_type))
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
				cur.close()
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
				error = 'Image not Verified or password is incorrect'
				return render_template('login.html', error=error)
			
		else:
			error = 'Already Login or Email was not found!'
			return render_template('login.html', error=error)
	return render_template('login.html')

@app.route('/verifyEmail', methods=['GET','POST'])
def verifyEmail():
	if request.method == 'POST':
		theOTP = request.form['eotp']
		if 'tempName' in session and 'tempOTP' in session and 'tempEmail' in session and 'tempPassword' in session and 'tempUT' in session:
			dbName = session['tempName']
			mOTP = session['tempOTP']
			dbEmail = session['tempEmail']
			dbPassword = session['tempPassword']
			dbUser_type = session['tempUT']
			dbImgdata = session['tempImage']
			if(theOTP == mOTP):
				cur = mysql.connection.cursor()
				ar = cur.execute('INSERT INTO users(name, email, password, user_type, user_image, user_login) values(%s,%s,%s,%s,%s,%s)', (dbName, dbEmail, dbPassword, dbUser_type, dbImgdata, 0))
				mysql.connection.commit()
				cur.close()
				session.clear()
				if ar > 0:
					flash("Thanks for registering! You are sucessfully verified!.")
					return  redirect(url_for('login'))
				else:
					flash("Error Occurred!")
					return  redirect(url_for('login')) 
			else:
				return render_template('register.html',error="OTP is incorrect.")
		else:
			flash("Session data is missing. Please go through the registration process first.")
			return redirect(url_for('register'))
	return render_template('verifyEmail.html')


@app.route('/logout', methods=["GET", "POST"])
def logout():
	cur = mysql.connection.cursor()
	lbr = cur.execute('UPDATE users set user_login = 0 where email = %s and uid = %s',(session['email'],session['uid']))
	mysql.connection.commit()
	session.clear()
	if lbr > 0:
		# print(session['email']+" Logout")
		return "success"
	else:
		return "error"

@app.route('/contact', methods=['GET','POST'])
def contact():
	if request.method == 'POST':
		careEmail = "narender.rk10@gmail.com"
		cname = request.form['cname']
		cemail = request.form['cemail']
		cquery = request.form['cquery']
		msg1 = Message('Hello', sender = sender, recipients = [cemail])
		msg2 = Message('Hello', sender = sender, recipients = [careEmail])
		msg1.body = "YOUR QUERY WILL BE PROCESSED! WITHIN 24 HOURS"
		msg2 = Message('Hello', sender = sender, recipients = [careEmail])
		msg2.body = " ".join(["NAME:", cname, "EMAIL:", cemail, "QUERY:", cquery]) 
		mail.send(msg1)
		mail.send(msg2)
		flash('Your Query has been recorded.', 'success')
	return render_template('contact.html')

@app.route('/lostpassword', methods=['GET','POST'])
def lostpassword():
	if request.method == 'POST':
		lpemail = request.form['lpemail']
		cur = mysql.connection.cursor()
		results = cur.execute('SELECT * from users where email = %s' , [lpemail])
		if results > 0:
			sesOTPfp = generateOTP()
			session['tempOTPfp'] = sesOTPfp
			session['seslpemail'] = lpemail
			msg1 = Message('MyProctor.ai - OTP Verification for Lost Password', sender = sender, recipients = [lpemail])
			msg1.body = "Your OTP Verfication code for reset password is "+sesOTPfp+"."
			mail.send(msg1)
			return redirect(url_for('verifyOTPfp')) 
		else:
			return render_template('lostpassword.html',error="Account not found.")
	return render_template('lostpassword.html')

@app.route("/professor_index")
@user_role_professor
def professor_index():
	return render_template('professor_index.html')

@app.route("/student_index")
@user_role_student
def student_index():
	return render_template('student_index.html')

@app.route("/create-test", methods = ['GET', 'POST'])
@user_role_professor
def create_test():
	form = UploadForm()
	if request.method=='POST' and form.validate_on_submit():
		test_id = generate_slug(2)
		# filename = secure_filename(form.doc.data.filename)
		filestream = form.doc.data
		filestream.seek(0)
		ef = pd.read_csv(filestream)
		fields = ['qid','q','a','b','c','d','ans','marks']
		df = pd.DataFrame(ef, columns = fields)
		print(df)
		cur = mysql.connection.cursor()
		for row in df.index:
			cur.execute('INSERT INTO questions(test_id,qid,q,a,b,c,d,ans,marks,uid) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', (test_id, df['qid'][row], df['q'][row], df['a'][row], df['b'][row], df['c'][row], df['d'][row], df['ans'][row], df['marks'][row], session['uid']))
			cur.connection.commit()
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
		cur.execute('INSERT INTO teachers (email, test_id, test_type, start, end, duration, show_ans, password, subject, topic, neg_marks, calc, uid) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
			(session['email'], test_id, "objective", start_date_time, end_date_time, duration, 1, password, subject, topic, neg_mark, calc, session['uid']))
		mysql.connection.commit()
		cur.close()
		flash(f'Exam ID: {test_id}', 'success')
		return redirect(url_for('professor_index'))
	return render_template('create_test.html', form = form)

@app.route('/generate_test')
@user_role_professor
def generate_test():
	return render_template('generate_test.html')

@app.route('/test_generate', methods=["GET", "POST"])
@user_role_professor
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

@app.route('/viewquestions', methods=['GET'])
@user_role_professor
def viewquestions():
	cur = mysql.connection.cursor()
	results = cur.execute('SELECT test_id from teachers where email = %s and uid = %s', (session['email'],session['uid']))
	if results > 0:
		cresults = cur.fetchall()
		cur.close()
		return render_template("viewquestions.html", cresults = cresults)
	else:
		return render_template("viewquestions.html", cresults = None)

@app.route('/displayquestions',methods=['POST'])
@user_role_professor
def displayquestions():
	tid = request.form['choosetid']
	cur = mysql.connection.cursor()
	cur.execute('SELECT * from questions WHERE test_id = %s', (tid,))
	## additional comma to make it tuple for single value tid
	results = cur.fetchall()
	cur.close()
	return render_template("displayquestions.html", callresults = results)

@app.route(f'/disptests', methods=['GET'])
def disptests():
	cur = mysql.connection.cursor()
	res = cur.execute('SELECT test_id,password,subject,topic FROM teachers WHERE uid = %s and email = %s',(session['uid'],session['email']))
	if res>0:
		tests = cur.fetchall()
		cur.close()
		return render_template('disptests.html',tests = tests)
	return render_template('disptests.html',tests = None)


@app.route('/deltidlist', methods=['GET'])
@user_role_professor
def deltidlist():
	cur = mysql.connection.cursor()
	results = cur.execute('SELECT * from teachers where email = %s and uid = %s', (session['uid'],session['email']))
	# print(results)
	if results > 0:
		cresults = cur.fetchall()
		# print(cresults)
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


@app.route('/deldispques', methods=['POST'])
@user_role_professor
def deldispques():
	if request.method == 'POST':
		tidoption = request.form['choosetid']
		cur = mysql.connection.cursor()
		cur.execute('SELECT * from questions where test_id = %s and uid = %s', (tidoption,session['uid']))
		callresults = cur.fetchall()
		cur.close()
		return render_template("deldispques.html", callresults = callresults, tid = tidoption)

@app.route('/delete_questions/<testid>', methods=['POST'])
@user_role_professor
def delete_questions(testid):
	cur = mysql.connection.cursor()
	msg = '' 
	if request.method == 'POST':
		testqdel = request.json['qids']
		if testqdel:
			if ',' in testqdel:
				testqdel = testqdel.split(',')
				for getid in testqdel:
					cur.execute('DELETE FROM questions WHERE test_id = %s and qid =%s and uid = %s', (testid,getid,session['uid']))
					mysql.connection.commit()
				resp = jsonify('<span style=\'color:green;\'>Questions deleted successfully</span>')
				resp.status_code = 200
				return resp
			else:
				cur.execute('DELETE FROM questions WHERE test_id = %s and qid =%s and uid = %s', (testid,testqdel,session['uid']))
				mysql.connection.commit()
				resp = jsonify('<span style=\'color:green;\'>Questions deleted successfully</span>')
				resp.status_code = 200
				return resp

@app.route('/<testid>/<qid>')
@user_role_professor
def del_qid(testid, qid):
	cur = mysql.connection.cursor()
	results = cur.execute('DELETE FROM questions where test_id = %s and qid = %s and uid = %s', (testid,qid,session['uid']))
	mysql.connection.commit()
	if results>0:
		msg="Deleted successfully"
		flash('Deleted successfully.', 'success')
		cur.close()
		return render_template("deldispques.html", success=msg)
	else:
		return render_template('deldispques.html')

################### UPDATE QUESTIONS ######################

@app.route('/updatetidlist', methods=['GET'])
@user_role_professor
def updatetidlist():
	cur = mysql.connection.cursor()
	results = cur.execute('SELECT * from teachers where email = %s and uid = %s', (session['uid'],session['email']))
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
		return render_template("updatetidlist.html", cresults = testids)
	else:
		return render_template("updatetidlist.html", cresults = None)

@app.route('/updatedispques', methods=['GET','POST'])
@user_role_professor
def updatedispques():
	if request.method == 'POST':
		tidoption = request.form['choosetid']
		# et = examtypecheck(tidoption)
		cur = mysql.connection.cursor()
		cur.execute('SELECT * from questions where test_id = %s and uid = %s', (tidoption,session['uid']))
		callresults = cur.fetchall()
		cur.close()
		return render_template("updatedispques.html", callresults = callresults)

@app.route('/update/<testid>/<qid>', methods=['GET','POST'])
@user_role_professor
def update_quiz(testid, qid):
	if request.method == 'GET':
		cur = mysql.connection.cursor()
		cur.execute('SELECT * FROM questions where test_id = %s and qid =%s and uid = %s', (testid,qid,session['uid']))
		uresults = cur.fetchall()
		mysql.connection.commit()
		return render_template("updateQuestions.html", uresults=uresults)
	if request.method == 'POST':
		ques = request.form['ques']
		ao = request.form['ao']
		bo = request.form['bo']
		co = request.form['co']
		do = request.form['do']
		anso = request.form['anso']
		markso = request.form['mko']
		cur = mysql.connection.cursor()
		cur.execute('UPDATE questions SET q = %s, a = %s, b = %s, c = %s, d = %s, ans = %s, marks = %s where test_id = %s and qid = %s and uid = %s', (ques,ao,bo,co,do,anso,markso,testid,qid,session['uid']))
		cur.connection.commit()
		flash('Updated successfully.', 'success')
		cur.close()
		return redirect(url_for('updatetidlist'))
	else:
		flash('ERROR  OCCURED.', 'error')
		return redirect(url_for('updatetidlist'))
	
def neg_marks(email,testid,negm):
	cur=mysql.connection.cursor()
	results = cur.execute("select marks,q.qid as qid, \
				q.ans as correct, ifnull(s.ans,0) as marked from questions q inner join \
				students s on  s.test_id = q.test_id and s.test_id = %s \
				and s.email = %s and s.qid = q.qid group by q.qid \
				order by q.qid asc", (testid, email))
	data=cur.fetchall()

	sum=0.0
	for i in range(results):
		if(str(data[i]['marked']).upper() != '0'):
			if(str(data[i]['marked']).upper() != str(data[i]['correct']).upper()):
				sum=sum - (negm/100) * int(data[i]['marks'])
			elif(str(data[i]['marked']).upper() == str(data[i]['correct']).upper()):
				sum+=int(data[i]['marks'])
	return sum

# def totmarks(email,tests): 
# 	cur = mysql.connection.cursor()
# 	for test in tests:
# 		testid = test['test_id']
# 		results=cur.execute("select neg_marks from teachers where test_id=%s",[testid])
# 		results=cur.fetchone()
# 		negm = results['neg_marks']
# 		data = neg_marks(email,testid,negm)
# 		return data

def marks_calc(email,testid):
		cur = mysql.connection.cursor()
		results=cur.execute("select neg_marks from teachers where test_id=%s",[testid])
		results=cur.fetchone()
		negm = results['neg_marks']
		return neg_marks(email,testid,negm) 

@app.route('/<email>/tests-created')
@user_role_professor
def tests_created(email):
	if email == session['email']:
		cur = mysql.connection.cursor()
		results = cur.execute('select * from teachers where email = %s and uid = %s and show_ans = 1', (email,session['uid']))
		results = cur.fetchall()
		return render_template('tests_created.html', tests=results)
	else:
		flash('You are not authorized', 'danger')
		return redirect(url_for('professor_index'))

@app.route('/<email>/tests-created/<testid>', methods = ['POST','GET'])
@user_role_professor
def student_results(email, testid):
	if email == session['email']:
		if request.method =='GET':
			cur = mysql.connection.cursor()
			results = cur.execute('select users.name as name,users.email as email, studentTestInfo.test_id as test_id from studentTestInfo, users where test_id = %s and completed = 1 and  users.user_type = %s and studentTestInfo.email=users.email ', (testid,'student'))
			results = cur.fetchall()
			cur.close()
			final = []
			names = []
			scores = []
			count = 1
			for user in results:
				score = marks_calc(user['email'], user['test_id'])
				user['srno'] = count
				user['marks'] = score
				final.append([count, user['name'], score])
				names.append(user['name'])
				scores.append(score)
				count+=1
			return render_template('student_results.html', data=final, labels=names, values=scores)

###################################### Student DashBoard ##########################################

class TestForm(Form):
	test_id = StringField('Exam ID')
	password = PasswordField('Exam Password')
	img_hidden_form = HiddenField(label=(''))

############ take/give Exam #################
@app.route('/<email>/tests-given', methods = ['POST','GET'])
@user_role_student
def tests_given(email):
	if request.method == "GET":
		if email == session['email']:
			cur = mysql.connection.cursor()
			resultsTestids = cur.execute('select studenttestinfo.test_id as test_id from studenttestinfo,teachers where studenttestinfo.email = %s and studenttestinfo.uid = %s and studenttestinfo.completed=1 and teachers.test_id = studenttestinfo.test_id and teachers.show_ans = 1 ', (email, session['uid']))
			resultsTestids = cur.fetchall()
			cur.close()
			return render_template('tests_given.html', cresults = resultsTestids)
		else:
			flash('You are not authorized', 'danger')
		return redirect(url_for('student_index'))
	elif request.method == "POST":
		tidoption = request.form['choosetid']
		cur = mysql.connection.cursor()
		cur.execute('SELECT test_type from teachers where test_id = %s',[tidoption])
		callresults = cur.fetchone()
		cur.close()
		# if callresults['test_type'] == "objective":
		cur = mysql.connection.cursor()
		results = cur.execute('select distinct(students.test_id) as test_id, students.email as email, subject,topic,neg_marks from students,studenttestinfo,teachers where students.email = %s and teachers.test_type = %s and students.test_id = %s and students.test_id=teachers.test_id and students.test_id=studenttestinfo.test_id and studenttestinfo.completed=1', (email, "objective", tidoption))
		results = cur.fetchall()
		cur.close()
		results1 = []
		studentResults = None
		for a in results:
			results1.append(neg_marks(a['email'],a['test_id'],a['neg_marks']))
			studentResults = zip(results,results1)
		return render_template('obj_result_student.html', tests=studentResults)


@app.route('/<email>/student_test_history')
@user_role_student
def student_test_history(email):
	if email == session['email']:
		cur = mysql.connection.cursor()
		results = cur.execute('SELECT a.test_id, b.subject, b.topic \
			from studenttestinfo a, teachers b where a.test_id = b.test_id and a.email=%s  \
			and a.completed=1', [email])
		results = cur.fetchall()
		return render_template('student_test_history.html', tests=results)
	else:
		flash('You are not authorized', 'danger')
		return redirect(url_for('student_index'))


# @app.route("/give-test", methods = ['GET', 'POST'])
# @user_role_student
# def give_test():
# 	global duration, marked_ans, calc, subject, topic, proctortype
# 	form = TestForm(request.form)
# 	if request.method == 'POST' and form.validate():
# 		test_id = form.test_id.data
# 		password_candidate = form.password.data
# 		imgdata1 = form.img_hidden_form.data
# 		cur = mysql.connection.cursor()
# 		results = cur.execute('SELECT * from teachers where test_id = %s', [test_id])
# 		if results > 0:
# 			data = cur.fetchone()
# 			password = data['password']
# 			duration = data['duration']
# 			calc = data['calc']
# 			subject = data['subject']
# 			topic = data['topic']
# 			start = data['start']
# 			start = str(start)
# 			end = data['end']
# 			end = str(end)
# 			# proctortype = data['proctoring_type']
# 			# print(test_id)
# 			if password == password_candidate:
# 				now = datetime.now()
# 				now = now.strftime("%Y-%m-%d %H:%M:%S")
# 				now = datetime.strptime(now,"%Y-%m-%d %H:%M:%S")
# 				if datetime.strptime(start,"%Y-%m-%d %H:%M:%S") < now and datetime.strptime(end,"%Y-%m-%d %H:%M:%S") > now:
# 					results = cur.execute('SELECT time_to_sec(time_left) as time_left,completed from studentTestInfo where email = %s and test_id = %s', (session['email'], test_id))
# 					if results > 0:
# 						results = cur.fetchone()
# 						# print(results)
# 						is_completed = results['completed']
# 						if is_completed == 0:
# 							time_left = results['time_left']
# 							if time_left <= duration:
# 								duration = time_left
# 								results = cur.execute('SELECT qid , ans from students where email = %s and test_id = %s and uid = %s', (session['email'], test_id, session['uid']))
# 								marked_ans = {}
# 								if results > 0:
# 									results = cur.fetchall()
# 									for row in results:
# 										# print(row['qid'])
# 										qiddb = ""+row['qid']
# 										# print(qiddb)
# 										# print(type(marked_ans))
# 										marked_ans[qiddb] = row['ans']
# 									marked_ans = json.dumps(marked_ans)
# 						else:
# 							flash('Exam already given', 'success')
# 							return redirect(url_for('give_test'))
# 					else:
# 						cur.execute('INSERT into studentTestInfo (email, test_id,time_left,uid) values(%s,%s,SEC_TO_TIME(%s),%s)', (session['email'], test_id, duration, session['uid']))
# 						mysql.connection.commit()
# 						results = cur.execute('SELECT time_to_sec(time_left) as time_left,completed from studentTestInfo where email = %s and test_id = %s and uid = %s', (session['email'], test_id, session['uid']))
# 						if results > 0:
# 							results = cur.fetchone()
# 							is_completed = results['completed']
# 							if is_completed == 0:
# 								time_left = results['time_left']
# 								if time_left <= duration:
# 									duration = time_left
# 									results = cur.execute('SELECT * from students where email = %s and test_id = %s and uid = %s', (session['email'], test_id, session['uid']))
# 									marked_ans = {}
# 									if results > 0:
# 										results = cur.fetchall()
# 										for row in results:
# 											marked_ans[row['qid']] = row['ans']
# 										marked_ans = json.dumps(marked_ans)
# 				else:
# 					if datetime.strptime(start,"%Y-%m-%d %H:%M:%S") > now:
# 						flash(f'Exam start time is {start}', 'danger')
# 					else:
# 						flash(f'Exam has ended', 'danger')
# 					return redirect(url_for('give_test'))
# 				return redirect(url_for('test' , testid = test_id))
# 			else:
# 				flash('Invalid password', 'danger')
# 				return redirect(url_for('give_test'))
# 		flash('Invalid testid', 'danger')
# 		cur.close()
# 		return redirect(url_for('give_test'))
# 	return render_template('give_test.html', form = form)


@app.route("/give-test", methods = ['GET', 'POST'])
@user_role_student
def give_test():
	global duration, marked_ans, calc, subject, topic, proctortype
	form = TestForm(request.form)
	if request.method == 'POST' and form.validate():
		test_id = form.test_id.data
		password_candidate = form.password.data
		imgdata1 = form.img_hidden_form.data
		cur1 = mysql.connection.cursor()
		results1 = cur1.execute('SELECT user_image from users where email = %s and user_type = %s ', (session['email'],'student'))
		if results1 > 0:
			cresults = cur1.fetchone()
			imgdata2 = cresults['user_image']
			cur1.close()
			nparr1 = np.frombuffer(base64.b64decode(imgdata1), np.uint8)
			nparr2 = np.frombuffer(base64.b64decode(imgdata2), np.uint8)
			image1 = cv2.imdecode(nparr1, cv2.COLOR_BGR2GRAY)
			image2 = cv2.imdecode(nparr2, cv2.COLOR_BGR2GRAY)
			img_result  = DeepFace.verify(image1, image2, enforce_detection = False)
			if img_result["verified"] == True:
				cur = mysql.connection.cursor()
				results = cur.execute('SELECT * from teachers where test_id = %s', [test_id])
				if results > 0:
					data = cur.fetchone()
					password = data['password']
					duration = data['duration']
					calc = data['calc']
					subject = data['subject']
					topic = data['topic']
					start = data['start']
					start = str(start)
					end = data['end']
					end = str(end)
					proctortype = data['proctoring_type']
					if password == password_candidate:
						now = datetime.now()
						now = now.strftime("%Y-%m-%d %H:%M:%S")
						now = datetime.strptime(now,"%Y-%m-%d %H:%M:%S")
						if datetime.strptime(start,"%Y-%m-%d %H:%M:%S") < now and datetime.strptime(end,"%Y-%m-%d %H:%M:%S") > now:
							results = cur.execute('SELECT time_to_sec(time_left) as time_left,completed from studentTestInfo where email = %s and test_id = %s', (session['email'], test_id))
							if results > 0:
								results = cur.fetchone()
								is_completed = results['completed']
								if is_completed == 0:
									time_left = results['time_left']
									if time_left <= duration:
										duration = time_left
										results = cur.execute('SELECT qid , ans from students where email = %s and test_id = %s and uid = %s', (session['email'], test_id, session['uid']))
										marked_ans = {}
										if results > 0:
											results = cur.fetchall()
											for row in results:
												print(row['qid'])
												qiddb = ""+row['qid']
												print(qiddb)
												marked_ans[qiddb] = row['ans']
												marked_ans = json.dumps(marked_ans)
								else:
									flash('Exam already given', 'success')
									return redirect(url_for('give_test'))
							else:
								cur.execute('INSERT into studentTestInfo (email, test_id,time_left,uid) values(%s,%s,SEC_TO_TIME(%s),%s)', (session['email'], test_id, duration, session['uid']))
								mysql.connection.commit()
								results = cur.execute('SELECT time_to_sec(time_left) as time_left,completed from studentTestInfo where email = %s and test_id = %s and uid = %s', (session['email'], test_id, session['uid']))
								if results > 0:
									results = cur.fetchone()
									is_completed = results['completed']
									if is_completed == 0:
										time_left = results['time_left']
										if time_left <= duration:
											duration = time_left
											results = cur.execute('SELECT * from students where email = %s and test_id = %s and uid = %s', (session['email'], test_id, session['uid']))
											marked_ans = {}
											if results > 0:
												results = cur.fetchall()
												for row in results:
													marked_ans[row['qid']] = row['ans']
												marked_ans = json.dumps(marked_ans)
						else:
							if datetime.strptime(start,"%Y-%m-%d %H:%M:%S") > now:
								flash(f'Exam start time is {start}', 'danger')
							else:
								flash(f'Exam has ended', 'danger')
							return redirect(url_for('give_test'))
						return redirect(url_for('test' , testid = test_id))
					else:
						flash('Invalid password', 'danger')
						return redirect(url_for('give_test'))
				flash('Invalid testid', 'danger')
				return redirect(url_for('give_test'))
				cur.close()
			else:
				flash('Image not Verified', 'danger')
				return redirect(url_for('give_test'))
	return render_template('give_test.html', form = form)


@app.route('/give-test/<testid>', methods=['GET','POST'])
@user_role_student
def test(testid):
	global duration, marked_ans, calc, subject, topic
	if request.method == 'GET':
		try:
			data = {'duration': duration, 'marks': '', 'q': '', 'a': '', 'b':'','c':'','d':'' }
			return render_template('testquiz.html' ,**data, answers=marked_ans, calc=calc, subject=subject, topic=topic, tid=testid)
		except:
			return redirect(url_for('give_test'))
	else:
		cur = mysql.connection.cursor()
		flag = request.form['flag']
		if flag == 'get':
			num = request.form['no']
			results = cur.execute('SELECT test_id,qid,q,a,b,c,d,ans,marks from questions where test_id = %s and qid =%s',(testid, num))
			if results > 0:
				data = cur.fetchone()
				del data['ans']
				cur.close()
				return json.dumps(data)
		elif flag=='mark':
			qid = request.form['qid']
			ans = request.form['ans']
			cur = mysql.connection.cursor()
			results = cur.execute('SELECT * from students where test_id =%s and qid = %s and email = %s', (testid, qid, session['email']))
			if results > 0:
				cur.execute('UPDATE students set ans = %s where test_id = %s and qid = %s and email = %s', (testid, qid, session['email']))
				mysql.connection.commit()
				cur.close()
			else:
				cur.execute('INSERT INTO students(email,test_id,qid,ans,uid) values(%s,%s,%s,%s,%s)', (session['email'], testid, qid, ans, session['uid']))
				mysql.connection.commit()
				cur.close()
		elif flag=='time':
			cur = mysql.connection.cursor()
			time_left = request.form['time']
			try:
				cur.execute('UPDATE studentTestInfo set time_left=SEC_TO_TIME(%s) where test_id = %s and email = %s and uid = %s and completed=0', (time_left, testid, session['email'], session['uid']))
				mysql.connection.commit()
				cur.close()
				return json.dumps({'time':'fired'})
			except:
				pass
		else:
			cur = mysql.connection.cursor()
			cur.execute('UPDATE studentTestInfo set completed=1,time_left=sec_to_time(0) where test_id = %s and email = %s and uid = %s', (testid, session['email'],session['uid']))
			mysql.connection.commit()
			cur.close()
			flash("Exam submitted successfully", 'info')
			return json.dumps({'sql':'fired'})

@app.route('/randomize', methods = ['POST'])
def random_gen():
	if request.method == "POST":
		id = request.form['id']
		cur = mysql.connection.cursor()
		results = cur.execute('SELECT count(*) from questions where test_id = %s', [id])
		if results > 0:
			data = cur.fetchone()
			total = data['count(*)']
			nos = list(range(1,int(total)+1))
			random.Random(id).shuffle(nos)
			cur.close()
			return json.dumps(nos)

model = YOLO('yolov3u.pt')
# gaze = GazeTracking()

@app.route('/live_snapshot', methods = ['POST'])
@user_role_student
def live_snapshot():
	if request.method == "POST":
		if 'image' in request.form:
			imgData = request.form['image']
			testid = request.form['testid']
			# Remove the Data URL prefix
			_, base64_data = imgData.split(',', 1)

			# Decode the Base64-encoded image data
			image_data = base64.b64decode(base64_data)

			# Convert the binary data to a NumPy array
			np_arr = np.frombuffer(image_data, np.uint8)

			# Decode the image using OpenCV
			image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
			
			results = model.predict(image, save=True, save_txt=True)
			
			# Specify the specific objects you want to count
			target_class = [67.0, 0.0]
			dict = {67.0:'Cell Phone',0.0:'Person'}
			# Initialize counters
			object_counts = {obj: 0 for obj in target_class}

			for res in results:
				for item in res.boxes.cls:
					label = item.item()
					if label in target_class:
						object_counts[label] += 1

			mob_status = 0
			preson_status = 1

			# Print the counts of specific objects
			for obj, count in object_counts.items():
				if obj==67.0:
					if count>0: mob_status=1
				elif obj==0.0:
					if count>1: person_status =2
					elif count==1: person_status=0
				print(f"Number of {dict[obj]}s: {count}")
			
			ret, jpeg = cv2.imencode('.jpg', image)
			jpg_as_text = base64.b64encode(jpeg)
			cur = mysql.connection.cursor()
			results = cur.execute('INSERT INTO proctoring_log (email, name, test_id, img_log, phone_detection, person_status, uid) values(%s,%s,%s,%s,%s,%s,%s)',
				(session['email'], session['name'], testid, jpg_as_text,mob_status, person_status,session['uid']))
			mysql.connection.commit()
			cur.close()

			if(results > 0):
				return "recorded image of video"
			else:
				return "error in video"
			# gaze.refresh(image)

			# frame = gaze.annotated_frame()
			# eye_movements = ""

			# if gaze.is_blinking():
			# 	eye_movements = 1
			# 	print("Blinking")
			# elif gaze.is_right():
			# 	eye_movements = 4
			# 	print("Looking right")
			# elif gaze.is_left():
			# 	eye_movements = 3
			# 	print("Looking left")
			# elif gaze.is_center():
			# 	eye_movements = 2
			# 	print("Looking center")
			# else:
			# 	eye_movements = 0
			# 	print("Not found!")
			# print(eye_movements)
		return 'No Image Data'
	return 'success'

@app.route('/window_event', methods=['GET','POST'])
@user_role_student
def window_event():
	if request.method == "POST":
		testid = request.form['testid']
		cur = mysql.connection.cursor()
		results = cur.execute('INSERT INTO window_estimation_log (email, test_id, name, window_event, uid) values(%s,%s,%s,%s,%s)', (dict(session)['email'], testid, dict(session)['name'], 1, dict(session)['uid']))
		mysql.connection.commit()
		cur.close()
		if(results > 0):
			return "recorded window"
		else:
			return "error in window"


@app.route('/viewstudentslogs', methods=['GET'])
@user_role_professor
def viewstudentslogs():
	cur = mysql.connection.cursor()
	results = cur.execute('SELECT test_id from teachers where email = %s and uid = %s and proctoring_type = 0', (session['email'],session['uid']))
	if results > 0:
		cresults = cur.fetchall()
		cur.close()
		return render_template("viewstudentslogs.html", cresults = cresults)
	else:
		return render_template("viewstudentslogs.html", cresults = None)
	
@app.route('/displaystudentsdetails', methods=['GET','POST'])
@user_role_professor
def displaystudentsdetails():
	if request.method == 'POST':
		tidoption = request.form['choosetid']
		cur = mysql.connection.cursor()
		cur.execute('SELECT DISTINCT email,test_id from proctoring_log where test_id = %s', [tidoption])
		callresults = cur.fetchall()
		cur.close()
		return render_template("displaystudentsdetails.html", callresults = callresults)

def countwinstudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT COUNT(*) as wincount from window_estimation_log where test_id = %s and email = %s and window_event = 1', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	winc = [i['wincount'] for i in callresults]
	return winc

def countMobStudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT COUNT(*) as mobcount from proctoring_log where test_id = %s and email = %s and phone_detection = 1', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	mobc = [i['mobcount'] for i in callresults]
	return mobc

def countMTOPstudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT COUNT(*) as percount from proctoring_log where test_id = %s and email = %s and person_status = 1', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	perc = [i['percount'] for i in callresults]
	return perc

def countTotalstudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT COUNT(*) as total from proctoring_log where test_id = %s and email = %s', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	tot = [i['total'] for i in callresults]
	return tot


def displaywinstudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT * from window_estimation_log where test_id = %s and email = %s and window_event = 1', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	return callresults


@app.route('/studentmonitoringstats/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def studentmonitoringstats(testid,email):
	return render_template("stat_student_monitoring.html", testid = testid, email = email)

@app.route('/ajaxstudentmonitoringstats/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def ajaxstudentmonitoringstats(testid,email):
	win = countwinstudentslogs(testid,email)
	mob = countMobStudentslogs(testid,email)
	per = countMTOPstudentslogs(testid,email)
	tot = countTotalstudentslogs(testid,email)
	return jsonify({"win":win,"mob":mob,"per":per,"tot":tot})

@app.route('/displaystudentslogs/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def displaystudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT * from proctoring_log where test_id = %s and email = %s', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	return render_template("displaystudentslogs.html", testid = testid, email = email, callresults = callresults)

@app.route('/mobdisplaystudentslogs/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def mobdisplaystudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT * from proctoring_log where test_id = %s and email = %s and phone_detection = 1', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	return render_template("mobdisplaystudentslogs.html", testid = testid, email = email, callresults = callresults)

@app.route('/persondisplaystudentslogs/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def persondisplaystudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT * from proctoring_log where test_id = %s and email = %s and person_status = 1', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	return render_template("persondisplaystudentslogs.html",testid = testid, email = email, callresults = callresults)

# @app.route('/audiodisplaystudentslogs/<testid>/<email>', methods=['GET','POST'])
# @user_role_professor
# def audiodisplaystudentslogs(testid,email):
# 	cur = mysql.connection.cursor()
# 	cur.execute('SELECT * from proctoring_log where test_id = %s and email = %s', (testid, email))
# 	callresults = cur.fetchall()
# 	cur.close()
# 	return render_template("audiodisplaystudentslogs.html", testid = testid, email = email, callresults = callresults)

@app.route('/wineventstudentslogs/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def wineventstudentslogs(testid,email):
	callresults = displaywinstudentslogs(testid,email)
	return render_template("wineventstudentlog.html", testid = testid, email = email, callresults = callresults)


if __name__ == "__main__":
	app.run()


