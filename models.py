from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

#1-to-1 relationship between User and ExaminerProfile
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False) #admin, examiner, student
    is_approved = db.Column(db.Boolean, default=False)
    is_active_user = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    #1-to-1 relationship with ExaminerProfile
    examiner_profile = db.relationship('ExaminerProfile', backref='user', uselist=False, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ExaminerProfile(db.Model):
    __tablename__ = 'examiner_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    designation = db.Column(db.String(100), default='Faculty')
    contact_number = db.Column(db.String(20))


#1-to-many relationship between Course and Examination, Examination and ExaminationRubric, Examination and ExaminationSlot
class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='Active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    examinations = db.relationship('Examination', backref='course', cascade='all, delete-orphan', lazy=True)

class Examination(db.Model):
    __tablename__ = 'examinations'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    exam_type = db.Column(db.String(50), nullable=False) #viva, practical, project demo
    duration = db.Column(db.Integer, nullable=False) #in minutes
    max_marks = db.Column(db.Integer, nullable=False)

    # Examination timeline windows
    slot_creation_start = db.Column(db.Date, nullable=False)
    slot_creation_end = db.Column(db.Date, nullable=False)
    slot_booking_start = db.Column(db.Date, nullable=False)
    slot_booking_end = db.Column(db.Date, nullable=False)

    status = db.Column(db.String(30), default='Draft') #Draft, Slot Creation, Booking Open, Closes, Completed
    assigned_examiner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    rubrics = db.relationship('ExaminationRubric', backref='examination', cascade='all, delete-orphan', lazy=True)
    slots = db.relationship('ExaminationSlot', backref='examination', cascade='all, delete-orphan', lazy=True)

class ExaminationRubric(db.Model):
    __tablename__ = 'examination_rubrics'

    id = db.Column(db.Integer, primary_key=True)
    examination_id = db.Column(db.Integer, db.ForeignKey('examinations.id'), nullable=False)
    criterion_name = db.Column(db.String(120), nullable=False) #code quality
    max_marks = db.Column(db.Integer, nullable=False)
    weightage = db.Column(db.Integer, default=100)
    description = db.Column(db.String(255))


#1-to-many relationship between ExaminationSlot and Booking, Booking and Evaluation
class ExaminationSlot(db.Model):
    __tablename__ = 'examination_slots'

    id = db.Column(db.Integer, primary_key=True)
    examination_id = db.Column(db.Integer, db.ForeignKey('examinations.id'), nullable=False)
    examiner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    max_capacity = db.Column(db.Integer, nullable=False, default=1)
    available_seats = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), default='Available') #Available, Full, Cancelled, Completed

    examiner = db.relationship('User', foreign_keys=[examiner_id], backref='slots')

    bookings = db.relationship('Booking', backref='slot', cascade='all, delete-orphan', lazy=True)

class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    slot_id = db.Column(db.Integer, db.ForeignKey('examination_slots.id'), nullable=False)
    student_id = db.Column(db.String(100), db.ForeignKey('users.id'), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Booked') #Booked, Cancelled, Completed

    student = db.relationship('User', foreign_keys=[student_id])
    evaluation = db.relationship('Evaluation', backref='booking', uselist=False, cascade='all, delete-orphan')

class Evaluation(db.Model):
    __tablename__ = 'evaluations'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), unique=True, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    examination_id = db.Column(db.Integer, db.ForeignKey('examinations.id'), nullable=False)
    examiner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    total_marks = db.Column(db.Float, default=0.0)
    remarks = db.Column(db.Text)
    status = db.Column(db.String(20), default='Submitted')
    evaluated_at = db.Column(db.DateTime, default=datetime.utcnow)

    scores = db.relationship('EvaluationScore', backref='evaluation', cascade='all, delete-orphan', lazy=True)

class EvaluationScore(db.Model):
    __tablename__ = 'evaluation_scores'

    id = db.Column(db.Integer, primary_key=True)
    evaluation_id = db.Column(db.Integer, db.ForeignKey('evaluations.id'), nullable=False)
    rubric_id = db.Column(db.Integer, db.ForeignKey('examination_rubrics.id'), nullable=False)
    marks_obtained = db.Column(db.Float, nullable=False)

    rubric = db.relationship('ExaminationRubric')