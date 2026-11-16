from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import (db, User, ExaminerProfile, Course, Examination, ExaminationRubric, ExaminationSlot, Booking)

main_bp = Blueprint('main', __name__)

#Role-based access control decorator (RBAC)
def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please log in first", "warning")
                return redirect(url_for('main.login'))
            if current_user.role not in roles:
                flash("Access Denied: You do not have permission to access this page.", "danger")
                return redirect(url_for('main.index'))
            if current_user.role == 'examiner' and not current_user.is_approved:
                flash("Your account is pending admin approval.", "warning")
                return redirect(url_for('main.pending_approval'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


#Public Routes
@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/pending_approval')
@login_required
def pending_approval():
    return render_template('auth/pending_approval.html')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('main.admin_dashboard'))
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip()
        password = request.form.get('password', '')

        #Check by username or email
        user = User.query.filter((User.username == login_id) | (User.email == login_id)).first()

        #verify passowrd hash
        if user and user.check_password(password):
            if not user.is_active_user:
                flash("Your account has been deactivated. Contact admin.", "danger")
                return redirect(url_for('main.login'))
            
            login_user(user)

            #route for Admin login
            if user.role == 'admin':
                return redirect(url_for('main.admin_dashboard'))
            return redirect(url_for('main.index'))
        
        else:
            flash("Invalid login credentials", "danger")
    return render_template('auth/login.html')

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        full_name = request.form.get('full_name', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'student')

        if password != confirm_password:
            flash("Passwords do not match", "danger")
            return redirect(url_for('main.register'))

        if len(password) < 6:
            flash("Password must be at least 6 characters long", "danger")
            return redirect(url_for('main.register'))

        if User.query.filter(User.username == username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for('main.register'))

        if User.query.filter(User.email == email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for('main.register'))

        is_approved = True if role == 'student' else False  #Students auto-approved, examiners need admin approval

        new_user = User(
            username=username,
            email=email,
            full_name=full_name,
            role=role,
            is_approved=is_approved,
            is_active_user=True
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        if role == 'examiner':
            department = request.form.get('department', 'General')
            designation = request.form.get('designation', 'Faculty')
            contact_number = request.form.get('contact_number', '')

            profile = ExaminerProfile(
                user_id=new_user.id,
                department=department,
                designation=designation,
                contact_number=contact_number
            )
            db.session.add(profile)
            db.session.commit()

            flash("Registration successful! Examiner accounts require admin approval before login.", "info")
            return redirect(url_for('main.login'))
        
        else:
            flash("Registration successful! You can log in.", "success")
            return redirect(url_for('main.login'))
    
    return render_template('auth/register.html')


@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('main.index'))




#Admin Routes

@main_bp.route('/admin/dashboard')
@role_required('admin')
def admin_dashboard():
    total_courses = Course.query.count()
    total_exams = Examination.query.count()
    total_examiners = User.query.filter_by(role='examiner').count()
    total_students = User.query.filter_by(role='student').count()
    total_slots = ExaminationSlot.query.count()
    total_bookings = Booking.query.count()

    pending_examiners = User.query.filter_by(role='examiner', is_approved=False).all()
    recent_exams = Examination.query.order_by(Examination.id.desc()).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        total_courses=total_courses,
        total_exams=total_exams,
        total_examiners=total_examiners,
        total_students=total_students,
        total_slots=total_slots,
        total_bookings=total_bookings,
        pending_examiners=pending_examiners,
        recent_exams=recent_exams
    )

@main_bp.route('/admin/courses')
@role_required('admin')
def admin_courses():
    search = request.args.get('search', '').strip()
    if search:
        courses = Course.query.filter(
            (Course.code.ilike(f'%{search}%')) | (Course.name.ilike(f'%{search}%'))
        ).all()
    else:
        courses = Course.query.order_by(Course.id.desc()).all()
    return render_template('admin/courses.html', courses=courses, search=search)

@main_bp.route('/admin/courses/add', methods=['POST'])
@role_required('admin')
def admin_add_course():
    code = request.form.get('code', '').strip().upper()
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    status = request.form.get('status', 'Active')

    if not code or not name:
        flash("Course code and name are required.", "danger")
        return redirect(url_for('main.admin_courses'))

    if Course.query.filter_by(code=code).first():
        flash(f"Course code '{code}' already exists.", "danger")
        return redirect(url_for('main.admin_courses'))

    new_course = Course(code=code, name=name, description=description)
    db.session.add(new_course)
    db.session.commit()

    flash(f"Course '{code}' created successfully.", "success")
    return redirect(url_for('main.admin_courses'))

@main_bp.route('/admin/courses/edit/<int:course_id>', methods=['POST', 'GET'])
@role_required('admin')
def admin_edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    if request.method == 'POST':
        course.name = request.form.get('name', '').strip()
        course.description = request.form.get('description', '').strip()
        course.status = request.form.get('status', 'Active')
        db.session.commit()
        flash("Course updated successfully.", "success")
        return redirect(url_for('main.admin_courses'))
    return render_template('admin/edit_course.html', course=course)

@main_bp.route('/admin/courses/delete/<int:course_id>', methods=['POST'])
@role_required('admin')
def admin_delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    db.session.delete(course)
    db.session.commit()
    flash(f"Course '{course.code}' and all related exams removed.", "info")
    return redirect(url_for('main.admin_courses'))



#Admin Examiner Management Routes

@main_bp.route('/admin/examinations')
@role_required('admin')
def admin_examinations():
    search = request.args.get('search', '').strip()
    query = Examination.query
    if search:
        query = query.filter(Examination.name.ilike(f'%{search}%'))

    exams = query.order_by(Examination.id.desc()).all()
    courses = Course.query.filter_by(status='Active').all()
    examiners = User.query.filter_by(role='examiner', is_approved=True, is_active_user=True).all()
    
    return render_template('admin/examinations.html', exams=exams, courses=courses, examiners=examiners, search=search)


@main_bp.route('/admin/examinations/add', methods=['POST'])
@role_required('admin')
def admin_add_examination():
    course_id = request.form.get('course_id')
    name = request.form.get('name', '').strip()
    exam_type = request.form.get('exam_type', 'Viva')
    duration = int(request.form.get('duration', 30))
    max_marks = int(request.form.get('max_marks', 100))
    status = request.form.get('status', 'Draft')
    assigned_examiner_id = request.form.get('assigned_examiner_id') or None

    try:
        slot_creation_start = datetime.strptime(request.form.get('slot_creation_start'), '%d-%m-%Y').date()
        slot_creation_end = datetime.strptime(request.form.get('slot_creation_end'), '%d-%m-%Y').date()
        slot_booking_start = datetime.strptime(request.form.get('slot_booking_start'), '%d-%m-%Y').date()
        slot_booking_end = datetime.strptime(request.form.get('slot_booking_end'), '%d-%m-%Y').date()
    except (ValueError, TypeError):
        flash("Invalid data format.", "danger")
        return redirect(url_for('main.admin_examinations'))

    if slot_creation_start > slot_creation_end :
        flash("Slot creation cannot be started after end date.", "danger")
        return redirect(url_for('main.admin_examinations'))

    if slot_booking_start > slot_booking_end :
            flash("Slot booking cannot be started after end date.", "danger")
            return redirect(url_for('main.admin_examinations'))

    new_exam = Examination(
        course_id=course_id,
        name=name,
        exam_type=exam_type,
        duration=duration,
        max_marks=max_marks,
        slot_creation_start=slot_creation_start,
        slot_creation_end=slot_creation_end,
        slot_booking_start=slot_booking_start,
        slot_booking_end=slot_booking_end,
        status=status,
        assigned_examiner_id=assigned_examiner_id
    )
    db.session.add(new_exam)
    db.session.commit()

    flash("Examination scheduled successfully.", "success")
    return redirect(url_for('main.admin_examinations'))


@main_bp.route('/admin/examination/edit/<int:exam_id>', methods=['POST', 'GET'])
@role_required('admin')
def admin_edit_examination(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    if request.method == 'POST':
        exam.course_id = request.form.get('course_id')
        exam.name = request.form.get('name', '').strip()
        exam.exam_type = request.form.get('exam_type')
        exam.duration = int(request.form.get('duration', 30))
        exam.max_marks = int(request.form.get('max_marks', 100))
        exam.status = request.form.get('status')
        exam.assigned_examiner_id = request.form.get('assigned_examiner_id') or None

        try:
            exam.slot_creation_start = datetime.strptime(request.form.get('slot_creation_start'), '%d-%m-%Y').date()
            exam.slot_creation_end = datetime.strptime(request.form.get('slot_creation_end'), '%d-%m-%Y').date()
            exam.slot_booking_start = datetime.strptime(request.form.get('slot_booking_start'), '%d-%m-%Y').date()
            exam.slot_booking_end = datetime.strptime(request.form.get('slot_booking_end'), '%d-%m-%Y').date()
        except (ValueError, TypeError):
                flash("Invalid data format.", "danger")
                return redirect(url_for('main.admin_examinations', exam_id=exam.id))

        db.session.commit()
        flash("Examination updated successfully.", "success")
        return redirect(url_for('main.admin_examinations'))

    courses = Course.query.filter_by(status='Active').all()
    examiners = User.query.filter_by(role='examiner', is_approved=True).all()
    return render_template('admin/edit_examination.html', exam=exam, courses=courses, examiners=examiners)


@main_bp.route('/admin/examination/delete/<int:exam_id>', methods=['POST'])
@role_required('admin')
def admin_delete_examination(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    db.session.delete(exam)
    db.session.commit()
    flash(f"Examination '{exam.name}' deleted.", "info")
    return redirect(url_for('main.admin_examinations'))


@main_bp.route('/admin/examination/<int:exam_id>/status/<string:new_status>', methods=['POST'])
@role_required('admin')
def admin_update_exam_status(exam_id, new_status):
    exam = Examination.query.get_or_404(exam_id)
    if new_status in ['Draft', 'Slot Creation', 'Booking Open', 'Closed', 'Completed']:
        exam.status = new_status
        db.session.commit()
        flash(f"Examination status updated to '{new_status}'.", "success")
    return redirect(url_for('main.admin_examinations'))




# Examination Rubrics Management

@main_bp.route('/admin/examination/<int:exam_id>/rubrics', methods=['POST', 'GET'])
@role_required('admin')
def admin_rubrics(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    if request.method == 'POST':
        criterion_name = request.form.get('criterion_name', '').strip()
        max_marks = int(request.form.get('max_marks', 10))
        weightage = int(request.form.get('weightage', 100))
        description = request.form.get('description', '').strip()

        if not criterion_name:
            flash("Criterion name is required.", "danger")
            return redirect(url_for('main.admin_rubrics', exam_id=exam.id))

        new_rubric = ExaminationRubric(
            examination_id=exam.id,
            criterion_name=criterion_name,
            max_marks=max_marks,
            weightage=weightage,
            description=description
        )
        db.session.add(new_rubric)
        db.session.commit()
        flash("Evaluation criterion added.", "success")
        return redirect(url_for('main.admin_rubrics', exam_id=exam.id))

    rubrics = ExaminationRubric.query.filter_by(examination_id=exam.id).all()
    return render_template('admin/rubrics.html', exam=exam, rubrics=rubrics)

@main_bp.route('/admin/rubric/delete/<int:rubric_id>', methods=['POST'])
@role_required('admin')
def admin_delete_rubric(rubric_id):
    rubric = ExaminationRubric.query.get_or_404(rubric_id)
    exam_id = rubric.examination_id
    db.session.delete(rubric)
    db.session.commit()
    flash("Rubric deleted.", "info")
    return redirect(url_for('main.admin_rubrics', exam_id=exam_id))



# Examiner Approvals & Deactivation

@main_bp.route('/admin/examiners')
@role_required('admin')
def admin_examiners():
    search = request.args.get('search', '').strip()
    query = User.query.filter_by(role='examiner')
    if search:
        query = query.filter((User.full_name.ilike(f'%{search}%')) | (User.username.ilike(f'%{search}%')))
        examiners = query.order_by(User.id.desc()).all()
        return render_template('admin/examiners.html', examiners=examiners, search=search)


@main_bp.route('/admin/examiner/<int:user_id>/approve', methods=['POST'])
@role_required('admin')
def admin_approve_examiner(user_id):
    user= User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    flash(f"Examiner {user.full_name} has been approved.", "success")
    return redirect(url_for('main.admin_examiners'))

@main_bp.route('/admin/user/<int:user_id>/toggle_status', methods=['POST'])
@role_required('admin')
def admin_toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active_user = not user.is_active_user
    db.session.commit()
    status_str = "activated" if user.is_active_user else "deactivated"
    flash(f"User {user.username} has been {status_str}.", "info")
    return redirect(url_for('main.admin_examiners'))



# Global Search

@main_bp.route('/admin/search')
@role_required('admin')
def admin_search():
    q = request.args.get('q', '').strip()
    users, exams = [], []
    if q:
        users = User.query.filter((User.username.ilike(f'%{q}%')) | (User.full_name.ilike(f'%{q}%')) | (User.email.ilike(f'%{q}%'))).all()
        exams = Examination.query.filter(Examination.name.ilike(f'%{q}%')).all()

    return render_template('admin/search.html', q=q, users=users, exams=exams)