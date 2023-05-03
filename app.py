from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_mysqldb import MySQL
# from werkzeug.utils import secure_filename
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, DateTimeField, BooleanField, IntegerField, DecimalField, HiddenField, SelectField, RadioField
from flask_wtf import FlaskForm
from wtforms.fields import DateField, TimeField
from datetime import timedelta, datetime
from wtforms.validators import ValidationError, NumberRange,InputRequired,Length
from flask_wtf.file import FileField, FileRequired, FileAllowed
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

# app.config['MAIL_SERVER']='stackmail.gmail.com'
# app.config['MAIL_PORT'] = 587
# app.config['MAIL_USERNAME'] = '20ucs068@lnmiit.ac.in'
# app.config['MAIL_PASSWORD'] = 'Sonu$$2106'
# app.config['MAIL_USE_TLS'] = True
# app.config['MAIL_USE_SSL'] = False

app.secret_key = 'cvproject'
mysql = MySQL(app)
# mail = Mail(app)

# sender = '20ucs068@lnmiit.ac.in'

# def generateOTP() : 
#     digits = "0123456789"
#     OTP = "" 
#     for i in range(5) : 
#         OTP += digits[math.floor(random.random() * 10)] 
#     return OTP 

# @app.route("/register", methods=['GET','POST'])
# def register():
# 	if request.method == 'POST':
# 		name = request.form['name']
# 		email = request.form['email']
# 		password = request.form['password']
# 		user_type = request.form['user_type']
# 		imgdata = request.form['image_hidden']
# 		session.clear()
# 		session['tempName'] = name
# 		session['tempEmail'] = email
# 		session['tempPassword'] = password
# 		session['tempUT'] = user_type
# 		session['tempImage'] = imgdata
# 		sesOTP = generateOTP()
# 		session['tempOTP'] = sesOTP
# 		msg1 = Message('MyProctor.ai - OTP Verification', sender = sender, recipients = [email])
# 		msg1.body = "New Account opening - Your OTP Verfication code is "+sesOTP+"."
# 		mail.send(msg1)
# 		return redirect(url_for('verifyEmail')) 
# 	return render_template('register.html')
uid = 123456
email = "abc@abc.com"

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
	return render_template('index.html', messages = 'My name is Khan')

@app.route("/professor_index")
def professor_index():
	return render_template('professor_index.html')

@app.route("/create-test", methods = ['GET', 'POST'])
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
			cur.execute('INSERT INTO questions(test_id,qid,q,a,b,c,d,ans,marks,uid) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', (test_id, df['qid'][row], df['q'][row], df['a'][row], df['b'][row], df['c'][row], df['d'][row], df['ans'][row], df['marks'][row], uid))
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
			(email, test_id, "objective", start_date_time, end_date_time, duration, 1, password, subject, topic, neg_mark, calc, uid))
		mysql.connection.commit()
		cur.execute('UPDATE users SET examcredits = examcredits-1 where email = %s and uid = %s', (email,uid))
		mysql.connection.commit()
		cur.close()
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
