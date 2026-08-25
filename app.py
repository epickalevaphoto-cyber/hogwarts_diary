from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

python init_db.py

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hogwarts_secret_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hogwarts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Модели
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='teacher')
    name = db.Column(db.String(100))

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    students = db.relationship('Student', backref='course', lazy=True)
    subjects = db.relationship('Subject', backref='course', lazy=True)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    grades = db.relationship('Grade', backref='student', lazy=True)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    grades = db.relationship('Grade', backref='subject', lazy=True)

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'))
    value = db.Column(db.String(20))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    courses = Course.query.order_by(Course.year).all()
    return render_template('index.html', courses=courses)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Добро пожаловать в Хогвартс!', 'success')
            return redirect(url_for('index'))
        flash('Неверное имя пользователя или пароль', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

@app.route('/course/<int:course_id>')
def course_view(course_id):
    course = Course.query.get_or_404(course_id)
    students = Student.query.filter_by(course_id=course_id).all()
    subjects = Subject.query.filter_by(course_id=course_id).all()
    
    # Собираем оценки
    grades_data = {}
    for student in students:
        grades_data[student.id] = {}
        for subject in subjects:
            grade = Grade.query.filter_by(student_id=student.id, subject_id=subject.id).first()
            grades_data[student.id][subject.id] = grade.value if grade else ''
    
    return render_template('gradebook.html', 
                         course=course, 
                         students=students, 
                         subjects=subjects,
                         grades_data=grades_data,
                         is_teacher=current_user.is_authenticated)

@app.route('/update_grade', methods=['POST'])
@login_required
def update_grade():
    student_id = request.form.get('student_id')
    subject_id = request.form.get('subject_id')
    value = request.form.get('value')
    
    grade = Grade.query.filter_by(student_id=student_id, subject_id=subject_id).first()
    if grade:
        grade.value = value if value else None
        grade.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Оценка обновлена'})
    return jsonify({'success': False, 'message': 'Оценка не найдена'})

@app.route('/certificate/<int:student_id>')
def certificate(student_id):
    student = Student.query.get_or_404(student_id)
    course = Course.query.get(student.course_id)
    
    # Только для 7-го курса
    if course.year != 7:
        flash('Аттестат выдается только на 7-м курсе!', 'error')
        return redirect(url_for('course_view', course_id=course.id))
    
    subjects = Subject.query.filter_by(course_id=course.id).all()
    grades = {}
    for subject in subjects:
        grade = Grade.query.filter_by(student_id=student.id, subject_id=subject.id).first()
        grades[subject.name] = grade.value if grade else 'Не оценено'
    
    # Маппинг оценок для аттестата
    grade_map = {
        'Превосходно': 'Превосходно',
        'Выше ожидаемого': 'Выше ожидаемого',
        'Удовлетворительно': 'Удовлетворительно',
        'Слабо': 'Слабо',
        'Провал': 'Провал'
    }
    
    return render_template('certificate.html', 
                         student=student, 
                         course=course, 
                         subjects=subjects, 
                         grades=grades,
                         grade_map=grade_map)

@app.route('/generate_all_certificates')
@login_required
def generate_all_certificates():
    course_7 = Course.query.filter_by(year=7).first()
    if not course_7:
        flash('7-й курс не найден', 'error')
        return redirect(url_for('index'))
    
    students = Student.query.filter_by(course_id=course_7.id).all()
    for student in students:
        # Проверяем, все ли оценки выставлены
        subjects = Subject.query.filter_by(course_id=course_7.id).all()
        all_graded = True
        for subject in subjects:
            grade = Grade.query.filter_by(student_id=student.id, subject_id=subject.id).first()
            if not grade or not grade.value:
                all_graded = False
                break
        
        if not all_graded:
            flash(f'У студента {student.name} не все оценки выставлены!', 'warning')
    
    return redirect(url_for('course_view', course_id=course_7.id))

# Контекстный процессор для шаблонов
@app.context_processor
def utility_processor():
    def get_grade_color(value):
        colors = {
            'Превосходно': 'excellent',
            'Выше ожидаемого': 'above',
            'Удовлетворительно': 'satisfactory',
            'Слабо': 'poor',
            'Провал': 'fail'
        }
        return colors.get(value, '')
    return dict(get_grade_color=get_grade_color)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
