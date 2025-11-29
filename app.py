from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from models import db, User, Appointment, Department, Treatment, Availability
from datetime import datetime, date, time, timedelta
from sqlalchemy import or_


app = Flask(__name__)
app.config['SECRET_KEY'] = 'sadhana'


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
        session['user_id'] = new_user.id
        session['role'] = new_user.role
        return redirect('/patient_dashboard')

   return render_template('register.html')


@app.route("/login", methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form.get('Username')
        password = request.form.get('Password')
        usr = User.query.filter_by(name=username).first()  # fetch by username
        if usr:
            if usr.role == 'a':
                session['user_id'] = usr.id
                session['role'] = usr.role
                return redirect(url_for('admin_dashboard'))
            
            elif usr.role == 'd':
                session['user_id'] = usr.id
                session['role'] = usr.role
                return redirect(url_for('doctor_dashboard'))
            
            elif usr.role == 'p':
                session['user_id'] = usr.id
                session['role'] = usr.role
                return redirect(url_for('patient_dashboard'))
            else:
                return "Unknown Role"
        else:
            return "Invalid credentials, try again"
    return render_template('login.html')


@app.route('/admin_dashboard')
def admin_dashboard():
    doctors = User.query.filter_by(role='d').all()
    patients = User.query.filter_by(role='p').all()

    all_appointments = Appointment.query.all()
    upcoming = Appointment.query.filter_by(status='scheduled').all()
    past = Appointment.query.filter(
        Appointment.status.in_(['Completed', 'Cancelled'])
    ).all()

    return render_template(
        'admin_dashboard.html',
        doctors=doctors,
        patients=patients,
        appointments=all_appointments,
        upcoming_appointments=upcoming,
        past_appointments=past
    )




@app.route('/admin_patient_history/<int:patient_id>')
def admin_patient_history(patient_id):
    # ensure admin logged in (optional simple check)
    user_id = session.get('user_id')
    role = session.get('role')
    if not user_id or role != 'a':
        return redirect('/login')

    patient = User.query.get_or_404(patient_id)

    # all completed/cancelled appointments for this patient with any doctor
    appointments = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.status.in_(['Completed', 'Cancelled'])
    ).order_by(Appointment.date.desc()).all()

    history = []
    for appt in appointments:
        treatment = Treatment.query.filter_by(appointment_id=appt.id).first()
        if treatment:
            history.append({
                'visit_date': appt.date,
                'doctor_name': appt.doctor.name,
                'department_name': appt.doctor.department.name
                    if appt.doctor.department else '',
                'diagnosis': treatment.diagnosis,
                'prescription': treatment.prescription,
                'medicines': treatment.notes
            })

    return render_template(
        'patient_history.html',
        patient=patient,
        history=history,
        from_patient=False,     # not the logged-in patient
        from_admin=True         # flag for template if needed
    )





@app.route('/search_doctors', methods=['POST'])
def search_doctors():
    q = request.form.get('q', '').strip()

    doctors_q = User.query.filter(User.role == 'd')
    if q:
        like = f"%{q}%"
        doctors_q = doctors_q.filter(
            or_(
                User.name.ilike(like),
                User.specialization.ilike(like)
            )
        )

    doctors = doctors_q.all()
    patients = User.query.filter_by(role='p').all()

    all_appointments = Appointment.query.all()
    upcoming = Appointment.query.filter(Appointment.date >= date.today()).all()
    past = Appointment.query.filter(Appointment.date < date.today()).all()

    return render_template(
        'admin_dashboard.html',
        doctors=doctors,
        patients=patients,
        appointments=all_appointments,
        upcoming_appointments=upcoming,
        past_appointments=past
    )


@app.route('/search_patients', methods=['POST'])
def search_patients():
    q = request.form.get('q', '').strip()

    patients_q = User.query.filter(User.role == 'p')
    if q:
        like = f"%{q}%"
        patients_q = patients_q.filter(
            or_(
                User.name.ilike(like),
                User.contact.ilike(like),
                User.id.cast(db.String).ilike(like)
            )
        )

    patients = patients_q.all()
    doctors = User.query.filter_by(role='d').all()

    all_appointments = Appointment.query.all()
    upcoming = Appointment.query.filter(Appointment.date >= date.today()).all()
    past = Appointment.query.filter(Appointment.date < date.today()).all()

    return render_template(
        'admin_dashboard.html',
        doctors=doctors,
        patients=patients,
        appointments=all_appointments,
        upcoming_appointments=upcoming,
        past_appointments=past
    )





@app.route('/delete_doctor/<int:doctor_id>')
def delete_doctor(doctor_id):
    doctor = User.query.get_or_404(doctor_id)
    db.session.delete(doctor)
    db.session.commit()
    return redirect('/admin_dashboard')

@app.route('/blacklist_doctor/<int:doctor_id>')
def blacklist_doctor(doctor_id):
    doctor = User.query.get_or_404(doctor_id)
    doctor.blacklisted = True
    db.session.commit()
    return redirect('/admin_dashboard')


@app.route('/edit-doctor/<int:doctor_id>', methods=['GET', 'POST'])
def edit_doctor(doctor_id):
    doctor = User.query.get_or_404(doctor_id)
    departments = Department.query.all()

    if request.method == 'POST':
        doctor.name = request.form.get('name', doctor.name)
        doctor.email = request.form.get('email', doctor.email)
        doctor.contact = request.form.get('contact', doctor.contact)
        doctor.specialization = request.form.get('specialization', doctor.specialization)
        doctor.experience = request.form.get('experience', doctor.experience)
        dept_id = request.form.get('department_id')
        if dept_id:
            doctor.department_id = int(dept_id)
        db.session.commit()
        return redirect('/admin_dashboard')

    return render_template('add_doctor.html',
                           departments=departments,
                           doctor=doctor)



@app.route('/delete_patient/<int:patient_id>')
def delete_patient(patient_id):
    patient = User.query.get_or_404(patient_id)
    db.session.delete(patient)
    db.session.commit()
    return redirect('/admin_dashboard')

@app.route('/blacklist_patient/<int:patient_id>')
def blacklist_patient(patient_id):
    patient = User.query.get_or_404(patient_id)
    patient.blacklisted = True
    db.session.commit()
    return redirect('/admin_dashboard')

@app.route('/edit-patient/<int:patient_id>', methods=['GET', 'POST'])
def edit_patient(patient_id):
    patient = User.query.get_or_404(patient_id)

    if request.method == 'POST':
        patient.name = request.form.get('name', patient.name)
        patient.email = request.form.get('email', patient.email)
        patient.contact = request.form.get('contact', patient.contact)
        patient.gender = request.form.get('gender', patient.gender)
        # optional: dob, medical_history
        db.session.commit()
        return redirect('/admin_dashboard')

    return render_template('register.html', patient=patient)





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
    doctor_id = session.get('user_id')
    if not doctor_id:
        return redirect('/login')   

    doctor = User.query.filter_by(id=doctor_id).first()
    if not doctor:
        return "No Doctor Found"

    # upcoming appointments only for the top table
    upcoming_appointments = [a for a in doctor.appointments_as_doctor
                             if a.status == 'scheduled']

    # ALL appointments (past + upcoming) to build patient list
    all_appts = doctor.appointments_as_doctor
    patient_ids = {appt.patient_id for appt in all_appts}
    assigned_patients = User.query.filter(User.id.in_(patient_ids)).all()

    return render_template('doctor_dashboard.html',
                           doctor=doctor,
                           appointments=upcoming_appointments,
                           assigned_patients=assigned_patients)


@app.route('/update_status/<int:appt_id>/<status>')
def update_status(appt_id, status):
    doctor_id = session.get('user_id')
    if not doctor_id:
        return redirect('/login')

    appt = Appointment.query.get_or_404(appt_id)
    if appt.doctor_id != doctor_id:
        return "Not allowed"

    if status in ['Completed', 'Cancelled']:
        appt.status = status
        db.session.commit()

    return redirect('/doctor_dashboard')



@app.route("/logout")
def doctor_logout():
    session.clear()
    return redirect('/login')



@app.route('/provide_availability', methods=['GET', 'POST'])
def provide_availability():
    doctor_id = session.get('user_id')
    if not doctor_id:
        return redirect('/login')

    # fixed 1-hour slots per day
    FIXED_SLOTS = [
        # Morning slots
        ('morning_1', time(8, 0),  time(9, 0)),
        ('morning_2', time(9, 0),  time(10, 0)),
        ('morning_3', time(10, 0), time(11, 0)),
        ('morning_4', time(11, 0), time(12, 0)),

        # Evening slots
        ('evening_1', time(16, 0), time(17, 0)),
        ('evening_2', time(17, 0), time(18, 0)),
        ('evening_3', time(18, 0), time(19, 0)),
        ('evening_4', time(19, 0), time(20, 0)),
    ]

    # next 7 days from today
    today = date.today()
    week_dates = [today + timedelta(days=i) for i in range(7)]

    if request.method == 'POST':
        # loop over each date and slot
        for d in week_dates:
            for slot_name, start_t, end_t in FIXED_SLOTS:
                field_name = f"{d.isoformat()}_{slot_name}"

                # if already booked -> skip completely (do not change availability)
                booked = Appointment.query.filter_by(
                    doctor_id=doctor_id,
                    date=d,
                    time=start_t,          # IMPORTANT: use Time object, not string
                    status='scheduled'
                ).first()
                if booked:
                    continue

                # if checkbox is ticked, ensure availability exists
                if request.form.get(field_name):
                    exists = Availability.query.filter_by(
                        doctor_id=doctor_id,
                        date=d,
                        start_time=start_t,
                        end_time=end_t
                    ).first()
                    if not exists:
                        new_slot = Availability(
                            doctor_id=doctor_id,
                            date=d,
                            start_time=start_t,
                            end_time=end_t
                        )
                        db.session.add(new_slot)
                else:
                    # checkbox not ticked: remove availability if it exists and is not booked
                    avail = Availability.query.filter_by(
                        doctor_id=doctor_id,
                        date=d,
                        start_time=start_t,
                        end_time=end_t
                    ).first()
                    if avail:
                        db.session.delete(avail)

        db.session.commit()
        return redirect('/doctor_dashboard')

    # For GET: compute current status (available/booked) per slot for display
    week_view = []
    for d in week_dates:
        day_info = {'date': d, 'slots': []}
        for slot_name, start_t, end_t in FIXED_SLOTS:
            # is this slot booked?
            booked = Appointment.query.filter_by(
                doctor_id=doctor_id,
                date=d,
                time=start_t,          # same Time object comparison
                status='scheduled'
            ).first()

            # is this slot already available (but maybe not booked)?
            avail = Availability.query.filter_by(
                doctor_id=doctor_id,
                date=d,
                start_time=start_t,
                end_time=end_t
            ).first()

            day_info['slots'].append({
                'name': slot_name,
                'label': f"{start_t.strftime('%H:%M')} - {end_t.strftime('%H:%M')}",
                'field_name': f"{d.isoformat()}_{slot_name}",
                'is_booked': bool(booked),
                'is_available': bool(avail),
            })
        week_view.append(day_info)

    return render_template('provide_availability.html', week_view=week_view)




@app.route('/reschedule_appointment/<int:appt_id>')
def reschedule_appointment(appt_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    appt = Appointment.query.get_or_404(appt_id)
    if appt.patient_id != user_id:
        return "Not allowed"

    doctor = appt.doctor

    slots = (Availability.query
             .filter(Availability.doctor_id == doctor.id,
                     Availability.date >= date.today())
             .order_by(Availability.date, Availability.start_time)
             .all())

    booked_appts = Appointment.query.filter_by(
        doctor_id=doctor.id,
        status='scheduled'
    ).all()

    booked_keys = set(
        (ba.date, ba.time.strftime('%H:%M'))
        for ba in booked_appts
    )

    slot_view = []
    for s in slots:
        key = (s.date, s.start_time.strftime('%H:%M'))
        is_booked = key in booked_keys
        slot_view.append({'slot': s, 'is_booked': is_booked})

    return render_template(
        'reschedule_select_slot.html',
        appt=appt,
        doctor=doctor,
        slot_view=slot_view
    )







@app.route('/apply_reschedule/<int:appt_id>/<int:slot_id>')
def apply_reschedule(appt_id, slot_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    appt = Appointment.query.get_or_404(appt_id)
    if appt.patient_id != user_id:
        return "Not allowed"

    slot = Availability.query.get_or_404(slot_id)

    # prevent multiple appointments at the same date and time for the same doctor
    existing = Appointment.query.filter_by(
        doctor_id=slot.doctor_id,
        date=slot.date,
        time=slot.start_time,
        status='scheduled'
    ).first()

    # allow this same appointment to move, block if some other one occupies it
    if existing and existing.id != appt.id:
        return "This slot is already booked. Please choose another one."

    appt.doctor_id = slot.doctor_id  # usually same doctor
    appt.date = slot.date
    appt.time = slot.start_time
    appt.status = 'scheduled'
    db.session.commit()

    return redirect('/patient_dashboard')








@app.route('/check_availability/<int:doc_id>')
def check_availability(doc_id):
    doctor = User.query.get_or_404(doc_id)

    # get all future availability slots for this doctor
    slots = (Availability.query
             .filter(Availability.doctor_id == doc_id,
                     Availability.date >= date.today())
             .order_by(Availability.date, Availability.start_time)
             .all())

    # all booked appointments for this doctor
    booked_appointments = (Appointment.query
                           .filter_by(doctor_id=doc_id, status='scheduled')
                           .all())

    # Build set of (date, start_time) that are booked
    booked_keys = set(
        (appt.date,
         appt.time.strftime('%H:%M'))   # time is a datetime.time
        for appt in booked_appointments
    )

    slot_view = []
    for s in slots:
        key = (s.date, s.start_time.strftime('%H:%M'))
        is_booked = key in booked_keys
        slot_view.append({'slot': s, 'is_booked': is_booked})

    return render_template('doctor_availability.html',
                           doctor=doctor,
                           slot_view=slot_view)





@app.route('/book_appointment/<int:slot_id>')
def book_appointment(slot_id):
    patient_id = session.get('user_id')
    if not patient_id:
        return redirect('/login')

    slot = Availability.query.get_or_404(slot_id)

    # create time string matching what you use in check_availability
    start_str = slot.start_time.strftime('%H:%M')
    end_str = slot.end_time.strftime('%H:%M')
    time_str = f"{start_str} - {end_str}"

    # check if already booked
    existing = Appointment.query.filter_by(
        doctor_id=slot.doctor_id,
        date=slot.date,
        time=slot.start_time,
        status='scheduled'
    ).first()
    if existing:
        return "This slot is already booked. Please choose another one."

    new_appt = Appointment(
        patient_id=patient_id,
        doctor_id=slot.doctor_id,
        date=slot.date,
        time=slot.start_time,   # <-- use time object, not string
        status='scheduled'
    )
    db.session.add(new_appt)
    db.session.commit()

    return redirect('/patient_dashboard')







@app.route("/patient_dashboard")
def patient_dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    departments = Department.query.all()

    upcoming = Appointment.query.filter(
        Appointment.patient_id == user_id,
        Appointment.date >= date.today()
    ).all()

    past = Appointment.query.filter(
        Appointment.patient_id == user_id,
        Appointment.date < date.today()
    ).all()

    return render_template(
        'patient_dashboard.html',
        departments=departments,
        upcoming_appointments=upcoming,
        past_appointments=past
    )




@app.route('/search_doctors_patient', methods=['POST'])
def search_doctors_patient():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    dept_id = request.form.get('department_id')
    name = request.form.get('name', '').strip()

    doctors_q = User.query.filter(User.role == 'd')

    # filter by specialization/department
    if dept_id and dept_id != 'all':
        doctors_q = doctors_q.filter(User.department_id == int(dept_id))

    # optional filter by doctor name
    if name:
        like = f"%{name}%"
        doctors_q = doctors_q.filter(User.name.ilike(like))

    doctors = doctors_q.all()

    departments = Department.query.all()
    upcoming = Appointment.query.filter(
        Appointment.patient_id == user_id,
        Appointment.date >= date.today()
    ).all()
    past = Appointment.query.filter(
        Appointment.patient_id == user_id,
        Appointment.date < date.today()
    ).all()

    return render_template(
        'patient_dashboard.html',
        departments=departments,
        upcoming_appointments=upcoming,
        past_appointments=past,
        search_doctors=doctors
    )




@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    patient = User.query.get_or_404(user_id)

    if request.method == 'POST':
        patient.name = request.form.get('name', patient.name)
        patient.email = request.form.get('email', patient.email)
        patient.contact = request.form.get('contact', patient.contact)
        patient.gender = request.form.get('gender', patient.gender)
        # dob, medical_history are optional; fill if you add fields in HTML
        db.session.commit()
        return redirect('/patient_dashboard')

    # reuse register.html form with patient prefilled
    return render_template('register.html', patient=patient)



@app.route('/cancel_appointment/<int:appt_id>')
def cancel_appointment(appt_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    appt = Appointment.query.get_or_404(appt_id)
    if appt.patient_id != user_id:
        return "Not allowed"

    appt.status = 'Cancelled'
    db.session.commit()
    return redirect('/patient_dashboard')



@app.route('/patient_history/<int:patient_id>')
def patient_history(patient_id):
    doctor_id = session.get('user_id')
    if not doctor_id:
        return redirect('/login')

    patient = User.query.get_or_404(patient_id)

    appointments = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.doctor_id == doctor_id,
        Appointment.status.in_(['Completed', 'Cancelled'])
    ).all()

    history = []
    for appt in appointments:
        treatment = Treatment.query.filter_by(appointment_id=appt.id).first()
        if treatment:
            history.append({
                'visit_date': appt.date,
                'diagnosis': treatment.diagnosis,
                'prescription': treatment.prescription,
                'medicines': treatment.notes
            })

    return render_template(
        'patient_history.html',
        patient=patient,
        history=history
    )




@app.route('/my_history')
def my_history():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    patient = User.query.get_or_404(user_id)

    # get all appointments for this patient (any doctor)
    appointments = (Appointment.query
                    .filter_by(patient_id=user_id)
                    .order_by(Appointment.date.desc())
                    .all())

    history = []
    for appt in appointments:
        treatment = Treatment.query.filter_by(appointment_id=appt.id).first()
        if treatment:
            history.append({
                'visit_date': appt.date,
                'doctor_name': appt.doctor.name,
                'department_name': appt.doctor.department.name
                    if appt.doctor.department else '',
                'diagnosis': treatment.diagnosis,
                'prescription': treatment.prescription,
                'medicines': treatment.notes
            })

    return render_template(
        'patient_history.html',
        patient=patient,
        history=history,
        from_patient=True
    )





@app.route('/edit_history/<int:appointment_id>', methods=['GET', 'POST'])
def edit_history(appointment_id):
    # make sure doctor is logged in
    doctor_id = session.get('user_id')
    if not doctor_id:
        return redirect('/login')

    # load appointment (ensure it belongs to this doctor)
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.doctor_id != doctor_id:
        return "Not allowed"

    # get or create treatment row for this appointment
    treatment = Treatment.query.filter_by(appointment_id=appointment_id).first()
    if not treatment:
        treatment = Treatment(
            appointment_id=appointment_id,
            diagnosis='',
            prescription='',
            notes=''
        )
        db.session.add(treatment)
        db.session.commit()

    patient = User.query.get(appt.patient_id)
    department = patient.department if hasattr(patient, 'department') else None

    if request.method == 'POST':
        treatment.diagnosis = request.form.get('diagnosis', '')
        treatment.prescription = request.form.get('prescription', '')
        treatment.notes = request.form.get('notes', '')
        db.session.commit()
        return redirect('/doctor_dashboard')

    return render_template(
        'edit_history.html',
        appt=appt,
        patient=patient,
        department=department,
        treatment=treatment
    )






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
    app.run(debug=True)
