from app import app, db, User, Student, Grade, Subject, Course
from werkzeug.security import generate_password_hash

def init_db():
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Создаем учителей (декканов)
        teachers = [
            {'username': 'snape', 'password': 'snape123', 'role': 'teacher', 'name': 'Северус Снейп'},
            {'username': 'mcgonagall', 'password': 'mcgonagall123', 'role': 'teacher', 'name': 'Минерва Макгонагалл'},
            {'username': 'flitwick', 'password': 'flitwick123', 'role': 'teacher', 'name': 'Филиус Флитвик'},
            {'username': 'sprout', 'password': 'sprout123', 'role': 'teacher', 'name': 'Помона Стебль'},
            {'username': 'lana', 'password': 'lana123', 'role': 'admin', 'name': 'Лана МакДауэлл'},
        ]

        for t in teachers:
            user = User(
                username=t['username'],
                password=generate_password_hash(t['password']),
                role=t['role'],
                name=t['name']
            )
            db.session.add(user)

        # Предметы по курсам
        subjects_1 = ['Заклинания', 'Трансфигурация', 'Зельеварение', 'История магии', 'Травология', 'ЗоТИ', 'Маггловедение', 'Полеты на метле']
        subjects_2_7 = ['Заклинания', 'ЗоТИ', 'Зельеварение', 'История магии', 'Травология', 'Трансфигурация', 'Маггловедение', 'УЗМС', 'Прорицание']

        courses = []
        for year in range(1, 8):
            course = Course(year=year)
            db.session.add(course)
            db.session.flush()
            
            subjects = subjects_1 if year == 1 else subjects_2_7
            for subj_name in subjects:
                subject = Subject(name=subj_name, course_id=course.id)
                db.session.add(subject)
            courses.append(course)

        # Студенты (пример для каждого курса)
        students_data = [
            # 1 курс
            {'name': 'Гарри Поттер', 'course': 1},
            {'name': 'Гермиона Грейнджер', 'course': 1},
            {'name': 'Рон Уизли', 'course': 1},
            {'name': 'Драко Малфой', 'course': 1},
            # 2 курс
            {'name': 'Невилл Долгопупс', 'course': 2},
            {'name': 'Луна Лавгуд', 'course': 2},
            {'name': 'Джинни Уизли', 'course': 2},
            # 3 курс
            {'name': 'Сириус Блэк', 'course': 3},
            {'name': 'Римус Люпин', 'course': 3},
            {'name': 'Питер Петтигрю', 'course': 3},
            # 4 курс
            {'name': 'Виктор Крам', 'course': 4},
            {'name': 'Седрик Диггори', 'course': 4},
            {'name': 'Флер Делакур', 'course': 4},
            # 5 курс
            {'name': 'Джеймс Поттер', 'course': 5},
            {'name': 'Лили Эванс', 'course': 5},
            {'name': 'Северус Снейп', 'course': 5},
            # 6 курс
            {'name': 'Том Реддл', 'course': 6},
            {'name': 'Альбус Дамблдор', 'course': 6},
            {'name': 'Геллерт Грин-де-Вальд', 'course': 6},
            # 7 курс - для генерации аттестатов
            {'name': 'Thierry Alan Focelman', 'course': 7},
            {'name': 'Amelia Rubin Audley', 'course': 7},
            {'name': 'Agatha Grimm', 'course': 7},
            {'name': 'Cassius Blackthorn', 'course': 7},
        ]

        for s in students_data:
            course_obj = Course.query.filter_by(year=s['course']).first()
            if course_obj:
                student = Student(name=s['name'], course_id=course_obj.id)
                db.session.add(student)
                db.session.flush()
                
                # Создаем записи оценок для всех предметов на этом курсе
                subjects = Subject.query.filter_by(course_id=course_obj.id).all()
                for subject in subjects:
                    grade = Grade(student_id=student.id, subject_id=subject.id, value=None)
                    db.session.add(grade)

        db.session.commit()
        print("База данных успешно инициализирована!")

if __name__ == '__main__':
    init_db()
