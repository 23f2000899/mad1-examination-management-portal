from app import create_app
from models import db, User, Course

app = create_app()

def init_database():
    with app.app_context():
        #to programatically create all the tables in models.py
        db.create_all()

        #Default admin if not exists
        if not User.query.filter_by(role='admin').first():
            admin = User(
                username='admin',
                email='admin@emp.com',
                full_name='Admin',
                role='admin',
                is_approved=True,
                is_active_user=True
            )
            admin.set_password('admin123')  #default password for admin
            db.session.add(admin)
            db.session.commit()
            print("Default admin created: admin/admin123")

        print("Database initialized successfully.")

if __name__ == '__main__':
    init_database()