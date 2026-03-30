import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func, or_
try:
    from app.models import db, User, Job
except ImportError:
    from models import db, User, Job
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'jobops-full-access-2026'

# Database Configuration
base_dir = os.path.abspath(os.path.dirname(__file__))
database_url = os.environ.get('DATABASE_URL')
if database_url:
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
else:
    database_url = f"sqlite:///{os.path.join(base_dir, '..', 'jobtracker_v2.db')}"

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    # If the user is logged in, show dashboard. If not, go to login.
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    search = request.args.get('search', '')
    query = Job.query.filter_by(user_id=current_user.id)
    if search:
        query = query.filter(Job.company_name.ilike(f'%{search}%') | Job.role.ilike(f'%{search}%'))
    
    jobs = query.order_by(Job.date_applied.desc()).all()
    stats = {
        'total': len(jobs),
        'selected': sum(1 for j in jobs if j.status == 'Selected'),
        'interviews': sum(1 for j in jobs if j.status == 'Interview'),
        'rejected': sum(1 for j in jobs if j.status == 'Rejected')
    }
    recent_activity = Job.query.filter_by(user_id=current_user.id).order_by(Job.date_applied.desc()).limit(5).all()
    return render_template('dashboard.html', jobs=jobs, stats=stats, recent_activity=recent_activity)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_job():
    if request.method == 'POST':
        date_applied_input = request.form.get('date_applied')
        if date_applied_input:
            try:
                date_applied = datetime.strptime(date_applied_input, '%Y-%m-%d')
            except ValueError:
                date_applied = datetime.utcnow()
        else:
            date_applied = datetime.utcnow()

        new_job = Job(
            company_name=request.form.get('company_name'),
            role=request.form.get('role'),
            location=request.form.get('location'),
            salary=request.form.get('salary'),
            date_applied=date_applied,
            status=request.form.get('status', 'Applied'),
            notes=request.form.get('notes'),
            interview_date=request.form.get('interview_date'),
            interview_round=request.form.get('interview_round'),
            interview_status=request.form.get('interview_status'),
            interview_feedback=request.form.get('interview_feedback'),
            user_id=current_user.id
        )
        db.session.add(new_job)
        db.session.commit()
        flash('Application Saved!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_job(id):
    job = Job.query.get_or_404(id)
    if request.method == 'POST':
        job.status = request.form.get('status')
        job.interview_date = request.form.get('interview_date')
        job.interview_round = request.form.get('interview_round')
        job.interview_status = request.form.get('interview_status')
        job.interview_feedback = request.form.get('interview_feedback')
        db.session.commit()
        flash('Tracking info updated!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit.html', job=job)

@app.route('/delete/<int:id>')
@login_required
def delete_job(id):
    job = Job.query.get_or_404(id)
    
    # Security check: Ensure the user owns this job before deleting
    if job.user_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('dashboard'))
    
    db.session.delete(job)
    db.session.commit()
    
    flash(f'Application for {job.company_name} deleted.', 'warning')
    return redirect(url_for('dashboard'))

@app.route('/companies')
@login_required
def companies():
    jobs = Job.query.filter_by(user_id=current_user.id).order_by(Job.company_name).all()
    return render_template('companies.html', jobs=jobs)

@app.route('/interviews')
@login_required
def interviews():
    interview_jobs = Job.query.filter(
        Job.user_id == current_user.id,
        or_(
            Job.status == 'Interview',
            Job.interview_date.isnot(None),
            Job.interview_status.isnot(None),
            Job.interview_round.isnot(None)
        )
    ).order_by(Job.interview_date.asc()).all()
    return render_template('interviews.html', jobs=interview_jobs)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        if request.form.get('form_type') == 'profile':
            current_user.full_name = request.form.get('full_name')
            current_user.email = request.form.get('email')
            current_user.phone = request.form.get('phone')
            resume = request.files.get('resume')
            if resume and resume.filename:
                filename = secure_filename(resume.filename)
                resume.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                current_user.resume_filename = filename
            db.session.commit()
            flash('Profile updated successfully.', 'success')
        elif request.form.get('form_type') == 'password':
            old_password = request.form.get('old_password')
            new_password = request.form.get('new_password')
            if current_user and check_password_hash(current_user.password, old_password):
                current_user.password = generate_password_hash(new_password)
                db.session.commit()
                flash('Password updated successfully.', 'success')
            else:
                flash('Current password is incorrect.', 'danger')
        return redirect(url_for('profile'))

    total_apps = Job.query.filter_by(user_id=current_user.id).count()
    resume_url = None
    if getattr(current_user, 'resume_filename', None):
        resume_url = url_for('static', filename=f'uploads/{current_user.resume_filename}')
    return render_template('profile.html', total_apps=total_apps, resume_url=resume_url)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.before_request
def init_db():
    app.before_request_funcs[None].remove(init_db)
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin', password=generate_password_hash('admin123')))
        db.session.commit()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)