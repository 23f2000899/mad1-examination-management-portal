from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, ExaminerProfile

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
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip()
        password = request.form.get('password', '')

        #Check by username or email
        user = User.query.filter((User.username == login_id) | (User.email == login_id)).first()

        if user and user.check_password(password):
            if not user.is_active_user:
                flash("Your account has been deactivated. Contact admin.", "danger")
                return redirect(url_for('main.login'))
            
            login_user(user)
            flash(f"Welcome, {user.full_name}!", "success")
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