from flask_sqlalchemy import SQLAlchemy
from datetime import date

db = SQLAlchemy()


class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(200))
    doctors = db.relationship('User', backref='department', lazy=True)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=True)
    name = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    password = db.Column(db.String(150), nullable=True)
    role = db.Column(db.String(10), nullable=False)
    contact = db.Column(db.String(100), nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    specialization = db.Column(db.String(100), nullable=True)   # Only filled for doctors
    experience = db.Column(db.Integer, nullable=True)           # Only filled for doctors
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=True)
    dob = db.Column(db.Date, nullable=True)
    medical_history = db.Column(db.Text, nullable=True)

    appointments_as_patient = db.relationship(
        'Appointment', 
        backref='patient', 
        lazy=True, 
        foreign_keys='Appointment.patient_id'
    )
    appointments_as_doctor = db.relationship(
        'Appointment', 
        backref='doctor', 
        lazy=True, 
        foreign_keys='Appointment.doctor_id'
    )



class Availability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    doctor = db.relationship('User', backref='availabilities')



class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id',ondelete='CASCADE'), nullable= False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id',ondelete='CASCADE'), nullable = False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(50))
    notes = db.Column(db.Text)
    treatments = db.relationship('Treatment', backref='appointment', lazy=True)


class Treatment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id', ondelete='CASCADE'), nullable=False)
    diagnosis = db.Column(db.Text, nullable=False)
    prescription = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text, nullable=False)




