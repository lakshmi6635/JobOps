from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    resume_filename = db.Column(db.String(255))
    jobs = db.relationship('Job', backref='owner', lazy=True, cascade="all, delete-orphan")

class Job(db.Model):
    __tablename__ = 'jobs'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100))
    salary = db.Column(db.String(50))
    date_applied = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Applied') # Applied, Interview, Rejected, Selected
    notes = db.Column(db.Text)
    company_website = db.Column(db.String(255))
    hr_contact = db.Column(db.String(255))
    
    # Interview Module Fields
    interview_date = db.Column(db.String(100)) 
    interview_round = db.Column(db.String(50)) # HR / Technical
    interview_status = db.Column(db.String(50)) # Scheduled / Completed
    interview_feedback = db.Column(db.Text)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)