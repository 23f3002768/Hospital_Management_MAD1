from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from models import db, User, Appointment, Department, Treatment, Availability
from datetime import datetime, timedelta


app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'

db.init_app(app)
@app.route("/")
def landing_page():
   return render_template('index.html')



@app.route("/register", methods=['GET', 'POST'])
def register():
   if request.method == 'POST':
       
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        contact = request.form['contact']

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return "Email already registered. Please use another email or login."
        
        new_user = User(
            name=name,
            email=email,
            password = password,
            contact = contact,
            role = 'p')
        db.session.add(new_user)
        db.session.commit()
        return redirect('/patient_dashboard')

   return render_template('register.html')


@app.route("/login", methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form.get('Username')
        password = request.form.get('Password')
        usr = User.query.filter_by(name=username).first()  # fetch by username
        if usr:# check hash
            if usr.role == 'a':
                return redirect(url_for('admin_dashboard'))
            elif usr.role == 'd':
                return redirect(url_for('doctor_dashboard'))
            elif usr.role == 'p':
                return redirect(url_for('patient_dashboard'))
            else:
                return "Unknown Role"
        else:
            return "Invalid credentials, try again"
    return render_template('login.html')


@app.route("/admin_dashboard")
def admin_dashboard():
   doctors = User.query.filter_by(role='d').all()
   patients = User.query.filter_by(role='p').all()
   appointments = Appointment.query.filter_by().all()
   return render_template('admin_dashboard.html', doctors=doctors, patients=patients, appointments = Appointment)


@app.route("/add_doctor", methods=['GET','POST'] )
def add_new_doctor():
    departments = Department.query.all()
    if request.method == 'POST':
        name = request.form['name']
        specialization = request.form['specialization']
        experience = request.form['experience']
        email = request.form['email']
        password = request.form['password']
        contact = request.form['contact']
        department_id = request.form['department_id']

        new_doctor = User(
            name=name,
            specialization=specialization,
            experience=experience,
            email=email,
            password=password,
            contact=contact,
            role='d',
            department_id = department_id
        )
        db.session.add(new_doctor)
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    return render_template('add_doctor.html', departments=departments)




@app.route("/doctor_dashboard")
def doctor_dashboard():
    doctor = User.query.filter_by(role='d').first()
    if not doctor:
       return "No Doctor Found"
    appointments = doctor.appointments_as_doctor
    patient_ids = {appt.patient_id for appt in appointments}
    assigned_patients = User.query.filter(User.id.in_(patient_ids)).all()
    return render_template('doctor_dashboard.html', doctor=doctor, appointments=appointments, assigned_patients = assigned_patients)

@app.route("/logout")
def doctor_logout():
    return redirect('/login')



@app.route("/provide_availability")
def provide_availability():
    # user_id = session.get('user_id')
    # if not user_id:
    #     return redirect ("/login")

    # doctor = User.query.get(user_id)
    # today = datetime.today().date()
    # dates = [today + timedelta(days=i) for i in range(7)]
    # all_slots = Availability.query.filter_by(doctor_id = doctor.id).filter(Availability.date.in_(dates)).all()
    # existing = { (s.date, s.start_time, s.end_time): s for s in all_slots }

    # # Prepare for form prefill: for each day, up to two slot dicts (or empty for no slot)
    # form_data = {}
    # for d in dates:
    #     # Collect any existing two slots for the date
    #     slots = [s for s in all_slots if s.date == d]
    #     slots_sorted = sorted(slots, key=lambda s: s.start_time) # earlier time first
    #     form_data[d] = [slots_sorted[0] if len(slots_sorted)>0 else None,
    #                     slots_sorted[1] if len(slots_sorted)>1 else None]

    # if request.method == 'POST':
    #     # Remove old slots for the week
    #     Availability.query.filter_by(doctor_id=doctor.id).filter(Availability.date.in_(dates)).delete(synchronize_session=False)
    #     db.session.commit()
    #     # For each day, process the two time slots if given
    #     for d in dates:
    #         for idx, label in enumerate(['morning', 'evening']):
    #             st_str = request.form.get(f'{label}_start_{d}')
    #             et_str = request.form.get(f'{label}_end_{d}')
    #             if st_str and et_str:
    #                 st = datetime.strptime(st_str, "%H:%M").time()
    #                 et = datetime.strptime(et_str, "%H:%M").time()
    #                 av = Availability(doctor_id=doctor.id, date=d, start_time=st, end_time=et)
    #                 db.session.add(av)
    #     db.session.commit()
    #     return redirect('/doctor_dashboard')
    return render_template('provide_availability.html', dates=dates, form_data=form_data)






@app.route("/patient_dashboard")
def patient_dashboard():
   departments = Department.query.all()
   user_id = 1
   appointments = Appointment.query.filter_by(patient_id=user_id).all()
   return render_template('patient_dashboard.html', departments=departments, appointments=appointments)


@app.route("/department/<int:dept_id>")
def department_details(dept_id):
    department = Department.query.get_or_404(dept_id)
    doctors = User.query.filter_by(department_id = dept_id, role = 'd').all()
    return render_template('department_details.html', department=department, doctors=doctors)


@app.route("/doctor_profile/<int:doc_id>")
def doctor_profile(doc_id):
    doctor = User.query.get_or_404(doc_id)
    availabilities = Availability.query.filter_by(doctor_id = doc_id).all()
    return render_template('doctor_profile.html', doctor=doctor, availabilities=availabilities)




def create_admin():
    admin_user = User.query.filter_by(email='admin@hospital.com', role='a').first()
    if not admin_user:
        hashed_pw = generate_password_hash('admin123')
        admin = User(
            name='Super Admin',
            email='admin@hospital.com',
            password=hashed_pw,
            role='a'
        )
        db.session.add(admin)
        db.session.commit()
        print('Admin user created!')
    else:
        print('Admin already exists.')


def seed_departments():
    from models import db, Department  # import your db and Department model
    
    default_departments = [
        {"name": "Cardiology", "description": "Heart specialists"},
        {"name": "Orthopedics", "description": "Bone and joint care"},
        {"name": "General Medicine", "description": "General health and checkups"},
        {"name": "Pediatrics", "description": "Child healthcare"},
        {"name": "ENT", "description": "Ear, Nose, Throat care"},
        {"name": "Neurology", "description": "Brain and nervous system care"},
        {"name": "Dermatology", "description": "Skin specialists"},
        {"name": "Gynecology", "description": "Women's health"},
        {"name": "Radiology", "description": "Imaging and scans"},
        {"name": "Oncology", "description": "Cancer treatment"},
        {"name": "Urology", "description": "Urinary tract and kidneys"},
        {"name": "Psychiatry", "description": "Mental health"},
        {"name": "Ophthalmology", "description": "Eye specialists"},
        {"name": "Anesthesiology", "description": "Anesthesia and pain management"},
        {"name": "Dentistry", "description": "Dental care"},
        {"name": "Emergency Medicine", "description": "Emergency cases"}
    ]
    
    for dep in default_departments:
        if not Department.query.filter_by(name=dep["name"]).first():
            db.session.add(Department(name=dep["name"], description=dep["description"]))
    db.session.commit()




if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_departments()
        create_admin()
    app.run()



app.run(debug=True)