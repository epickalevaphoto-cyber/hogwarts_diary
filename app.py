from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import sys

print(f"🐍 Python version: {sys.version}")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hogwarts_secret_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hogwarts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Модели данных
class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)

class Faculty(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(20))
    dean = db.Column(db.String(100))
    students = db.relationship('Student', backref='faculty', lazy=True)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    students = db.relationship('Student', backref='course', lazy=True)
    subjects = db.relationship('Subject', backref='course', lazy=True)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'))
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

def check_auth():
    return session.get('teacher_id') is not None

@app.route('/')
def index():
    courses = Course.query.order_by(Course.year).all()
    faculties = Faculty.query.all()
    return render_template('index.html', 
                         courses=courses, 
                         faculties=faculties,
                         is_auth=check_auth())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        teacher = Teacher.query.filter_by(username=username, password=password).first()
        if teacher:
            session['teacher_id'] = teacher.id
            session['teacher_name'] = teacher.name
            session['is_admin'] = teacher.is_admin
            flash('Добро пожаловать в Хогвартс!', 'success')
            return redirect(url_for('index'))
        flash('Неверное имя пользователя или пароль', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

@app.route('/course/<int:course_id>')
def course_view(course_id):
    course = Course.query.get_or_404(course_id)
    students = Student.query.filter_by(course_id=course_id).all()
    subjects = Subject.query.filter_by(course_id=course_id).all()
    faculties = Faculty.query.all()
    
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
                         faculties=faculties,
                         is_auth=check_auth(),
                         is_admin=session.get('is_admin', False))

@app.route('/update_grade', methods=['POST'])
def update_grade():
    if not check_auth():
        return jsonify({'success': False, 'message': 'Не авторизован'})
    
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
    """HTML версия аттестата (можно распечатать)"""
    student = Student.query.get_or_404(student_id)
    course = Course.query.get(student.course_id)
    
    if course.year != 7:
        flash('Аттестат выдается только на 7-м курсе!', 'error')
        return redirect(url_for('course_view', course_id=course.id))
    
    subjects = Subject.query.filter_by(course_id=course.id).all()
    grades = {}
    for subject in subjects:
        grade = Grade.query.filter_by(student_id=student.id, subject_id=subject.id).first()
        grades[subject.name] = grade.value if grade else 'Не оценено'
    
    return render_template('certificate.html', 
                         student=student, 
                         course=course, 
                         subjects=subjects, 
                         grades=grades,
                         faculties=Faculty.query.all())

@app.route('/generate_all_certificates')
def generate_all_certificates():
    if not check_auth():
        flash('Требуется авторизация', 'error')
        return redirect(url_for('login'))
    
    course_7 = Course.query.filter_by(year=7).first()
    if not course_7:
        flash('7-й курс не найден', 'error')
        return redirect(url_for('index'))
    
    students = Student.query.filter_by(course_id=course_7.id).all()
    missing_grades = []
    for student in students:
        subjects = Subject.query.filter_by(course_id=course_7.id).all()
        for subject in subjects:
            grade = Grade.query.filter_by(student_id=student.id, subject_id=subject.id).first()
            if not grade or not grade.value:
                missing_grades.append(f"{student.name} - {subject.name}")
    
    if missing_grades:
        flash(f'⚠️ Не все оценки выставлены у: {", ".join(missing_grades[:5])}', 'warning')
    else:
        flash('✅ Все оценки выставлены! Аттестаты готовы к просмотру и печати.', 'success')
    
    return redirect(url_for('course_view', course_id=course_7.id))

def init_database():
    with app.app_context():
        db.create_all()
        
        if Teacher.query.count() == 0:
            # Создаем факультеты
            faculties_data = [
                {'name': 'Гриффиндор', 'color': '#ae0001', 'dean': 'Minerva McGonagall'},
                {'name': 'Слизерин', 'color': '#1a472a', 'dean': 'Severus Snape'},
                {'name': 'Когтевран', 'color': '#0e1a40', 'dean': 'Filius Aitwick'},
                {'name': 'Пуффендуй', 'color': '#ffdb58', 'dean': 'Danna Serrut'},
            ]
            for f in faculties_data:
                faculty = Faculty(**f)
                db.session.add(faculty)
            db.session.flush()
            
            # Создаем учителей
            teachers = [
                {'username': 'snape', 'password': 'snape123', 'name': 'Северус Снейп', 'is_admin': False},
                {'username': 'mcgonagall', 'password': 'mcgonagall123', 'name': 'Минерва Макгонагалл', 'is_admin': False},
                {'username': 'flitwick', 'password': 'flitwick123', 'name': 'Филиус Флитвик', 'is_admin': False},
                {'username': 'sprout', 'password': 'sprout123', 'name': 'Помона Стебль', 'is_admin': False},
                {'username': 'lana', 'password': 'lana123', 'name': 'Лана МакДауэлл', 'is_admin': True},
            ]
            for t in teachers:
                teacher = Teacher(**t)
                db.session.add(teacher)
            
            # Создаем курсы и предметы
            subjects_1 = ['Заклинания', 'Трансфигурация', 'Зельеварение', 'История магии', 'Травология', 'ЗоТИ', 'Маггловедение', 'Полеты на метле']
            subjects_2_7 = ['Заклинания', 'ЗоТИ', 'Зельеварение', 'История магии', 'Травология', 'Трансфигурация', 'Маггловедение', 'УЗМС', 'Прорицание']
            
            for year in range(1, 8):
                course = Course(year=year)
                db.session.add(course)
                db.session.flush()
                
                subjects = subjects_1 if year == 1 else subjects_2_7
                for subj_name in subjects:
                    subject = Subject(name=subj_name, course_id=course.id)
                    db.session.add(subject)
            
            db.session.commit()
            
            # Добавляем студентов
            students_data = [
                {'name': 'Гарри Поттер', 'course': 1, 'faculty': 'Гриффиндор'},
                {'name': 'Гермиона Грейнджер', 'course': 1, 'faculty': 'Гриффиндор'},
                {'name': 'Рон Уизли', 'course': 1, 'faculty': 'Гриффиндор'},
                {'name': 'Драко Малфой', 'course': 1, 'faculty': 'Слизерин'},
                {'name': 'Невилл Долгопупс', 'course': 1, 'faculty': 'Гриффиндор'},
                {'name': 'Луна Лавгуд', 'course': 2, 'faculty': 'Когтевран'},
                {'name': 'Джинни Уизли', 'course': 2, 'faculty': 'Гриффиндор'},
                {'name': 'Колин Криви', 'course': 2, 'faculty': 'Гриффиндор'},
                {'name': 'Сириус Блэк', 'course': 3, 'faculty': 'Гриффиндор'},
                {'name': 'Римус Люпин', 'course': 3, 'faculty': 'Гриффиндор'},
                {'name': 'Питер Петтигрю', 'course': 3, 'faculty': 'Гриффиндор'},
                {'name': 'Виктор Крам', 'course': 4, 'faculty': 'Слизерин'},
                {'name': 'Седрик Диггори', 'course': 4, 'faculty': 'Пуффендуй'},
                {'name': 'Флер Делакур', 'course': 4, 'faculty': 'Когтевран'},
                {'name': 'Джеймс Поттер', 'course': 5, 'faculty': 'Гриффиндор'},
                {'name': 'Лили Эванс', 'course': 5, 'faculty': 'Гриффиндор'},
                {'name': 'Северус Снейп', 'course': 5, 'faculty': 'Слизерин'},
                {'name': 'Том Реддл', 'course': 6, 'faculty': 'Слизерин'},
                {'name': 'Альбус Дамблдор', 'course': 6, 'faculty': 'Гриффиндор'},
                {'name': 'Геллерт Грин-де-Вальд', 'course': 6, 'faculty': 'Когтевран'},
                {'name': 'Thierry Alan Focelman', 'course': 7, 'faculty': 'Гриффиндор'},
                {'name': 'Amelia Rubin Audley', 'course': 7, 'faculty': 'Слизерин'},
                {'name': 'Agatha Grimm', 'course': 7, 'faculty': 'Когтевран'},
                {'name': 'Cassius Blackthorn', 'course': 7, 'faculty': 'Пуффендуй'},
            ]
            
            for s in students_data:
                course = Course.query.filter_by(year=s['course']).first()
                faculty = Faculty.query.filter_by(name=s['faculty']).first()
                if course and faculty:
                    student = Student(name=s['name'], course_id=course.id, faculty_id=faculty.id)
                    db.session.add(student)
                    db.session.flush()
                    
                    subjects = Subject.query.filter_by(course_id=course.id).all()
                    for subject in subjects:
                        grade = Grade(student_id=student.id, subject_id=subject.id, value=None)
                        db.session.add(grade)
            
            db.session.commit()
            
            # Добавляем оценки для 7-го курса
            grades_7 = [
                ('Thierry Alan Focelman', {
                    'Заклинания': 'Превосходно',
                    'ЗоТИ': 'Превосходно',
                    'Зельеварение': 'Превосходно',
                    'История магии': 'Превосходчно',
                    'Травология': 'Превосходно',
                    'Трансфигурация': 'Превосходно',
                    'Маггловедение': 'Превосходно',
                    'УЗМС': 'Превосходно',
                    'Прорицание': 'Превосодно',
                }),
                ('Amelia Rubin Audley', {
                    'Заклинания': 'Превосходно',
                    'ЗоТИ': 'Превосходно',
                    'Зельеварение': 'Превосходно',
                    'История магии': 'Превосходно',
                    'Травология': 'Превосходно',
                    'Трансфигурация': 'Выше ожидаемого',
                    'Маггловедение': 'Выше ожидаемого',
                    'УЗМС': 'Выше ожидаемого',
                    'Прорицание': 'Выше ожидаемого',
                }),
                ('Agatha Grimm', {
                    'Заклинания': 'Превосходно',
                    'ЗоТИ': 'Выше ожидаемого',
                    'Зельеварение': 'Выше ожидаемого',
                    'История магии': 'Выше ожидаемого',
                    'Травология': 'Превосходно',
                    'Трансфигурация': 'Превосходно',
                    'Маггловедение': 'Превосходно',
                    'УЗМС': 'Удовлетворительно',
                    'Прорицание': 'Выше ожидаемого',
                }),
                ('Cassius Blackthorn', {
                    'Заклинания': 'Превосходно',
                    'ЗоТИ': 'Превосходно',
                    'Зельеварение': 'Превосходно',
                    'История магии': 'Превосходчно',
                    'Травология': 'Превосходно',
                    'Трансфигурация': 'Превосходно',
                    'Маггловедение': 'Превосходно',
                    'УЗМС': 'Превосходно',
                    'Прорицание': 'Превосодно',
                }),
            ]
            
            for name, grades_data in grades_7:
                student = Student.query.filter_by(name=name).first()
                if student:
                    for subj_name, grade_value in grades_data.items():
                        subject = Subject.query.filter_by(name=subj_name, course_id=7).first()
                        if subject:
                            grade = Grade.query.filter_by(student_id=student.id, subject_id=subject.id).first()
                            if grade:
                                grade.value = grade_value
            
            db.session.commit()
            print("✅ База данных успешно инициализирована!")

if __name__ == '__main__':
    init_database()
    app.run(debug=True, host='0.0.0.0', port=5000)
