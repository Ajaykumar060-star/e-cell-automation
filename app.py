from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus
import pandas as pd
from werkzeug.utils import secure_filename
import hashlib
from sqlalchemy import func
from io import StringIO
from flask import Response
from io import BytesIO
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
import zipfile
import tempfile
import json
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError
from bson.objectid import ObjectId
from ems_app.blueprints.students import bp as students_v2_bp
from ems_app.blueprints.allocation import bp as allocation_v2_bp
from ems_app.extensions import init_mongo

# ----------------------------------------
# Helpers for Excel/CSV transformations
# ----------------------------------------
def transform_excel(file_path: str) -> pd.DataFrame:
    """Read an Excel/CSV file and return a standardized DataFrame with columns:
    ID, Name, Email, Phone, Department, Year.

    - Supports alternate headers like SNO/Reg_No for ID, Name of the Student for Name,
      Dept for Department, year for Year.
    - If any required column is missing in the source, create it with empty strings.
    - Only these six columns are returned, in this exact order.
    """
    # Read file
    if file_path.lower().endswith('.csv'):
        df = pd.read_csv(file_path, dtype=str)
    elif file_path.lower().endswith(('.xlsx', '.xls')):
        # Read as strings to avoid numeric coercion (e.g., Reg_No becoming 1.234e+5)
        df = pd.read_excel(file_path, dtype=str)
    else:
        raise ValueError('Unsupported file format. Please upload CSV or Excel.')

    # Normalize source column names
    source_cols_original = list(df.columns)
    source_cols = [str(c).strip().lower() for c in source_cols_original]
    df.columns = source_cols

    def norm_key(s: str) -> str:
        import re
        return re.sub(r'[^a-z0-9]+', '', str(s).strip().lower())

    norm_map = {norm_key(col): col for col in df.columns}

    def resolve(*candidates):
        for cand in candidates:
            key = norm_key(cand)
            if key in norm_map:
                return norm_map[key]
        return None

    # Resolve aliases
    id_col = resolve('id', 'sno', 'reg_no', 'reg no', 'regno', 'register no', 'register_no')
    name_col = resolve('name', 'student_name', 'name of the student')
    email_col = resolve('email', 'mail id', 'mailid', 'mail-id')
    phone_col = resolve('phone', 'mobile', 'mobile_no', 'mobile no', 'phone_no', 'phone no')
    dept_col = resolve('department', 'dept')
    year_col = resolve('year', 'prog & year', 'prog & year.')

    # Fallback: header might not be in the first row. Try to detect within top 30 rows
    if not (name_col or email_col or id_col):
        if file_path.lower().endswith('.csv'):
            raw = pd.read_csv(file_path, header=None, dtype=str)
        else:
            raw = pd.read_excel(file_path, header=None, dtype=str)

        header_idx = None
        for i in range(min(30, len(raw))):
            row_vals = [str(x) for x in raw.iloc[i].tolist()]
            row_norms = [norm_key(x) for x in row_vals]
            if any(k in row_norms for k in [norm_key('name of the student'), norm_key('name')]):
                if any(k in row_norms for k in [norm_key('email'), norm_key('reg_no'), norm_key('reg no'), norm_key('regno'), norm_key('sno')]):
                    header_idx = i
                    new_cols = [str(x).strip().lower() for x in raw.iloc[i].tolist()]
                    df = raw.iloc[i+1:].copy()
                    df.columns = new_cols
                    # Rebuild maps and resolve
                    norm_map = {norm_key(col): col for col in df.columns}
                    id_col = resolve('id', 'sno', 'reg_no', 'reg no', 'regno', 'register no', 'register_no')
                    name_col = resolve('name', 'student_name', 'name of the student')
                    email_col = resolve('email', 'mail id', 'mailid', 'mail-id')
                    phone_col = resolve('phone', 'mobile', 'mobile_no', 'mobile no', 'phone_no', 'phone no')
                    dept_col = resolve('department', 'dept')
                    year_col = resolve('year', 'prog & year', 'prog & year.')
                    break

    # Build output with required columns only
    out_cols = ['ID', 'Name', 'Email', 'Phone', 'Department', 'Year']
    out = pd.DataFrame(columns=out_cols)

    # Helper to safely get series, else empty strings
    def get_series_or_empty(col_name: str):
        return df[col_name].astype(str).fillna('') if col_name in df.columns else pd.Series([''] * len(df))

    out['ID'] = get_series_or_empty(id_col) if id_col else pd.Series([''] * len(df))
    out['Name'] = get_series_or_empty(name_col) if name_col else pd.Series([''] * len(df))
    out['Email'] = get_series_or_empty(email_col) if email_col else pd.Series([''] * len(df))
    # Clean phone to keep only digits, max 10
    if phone_col and phone_col in df.columns:
        cleaned_phone = df[phone_col].astype(str).fillna('')
        cleaned_phone = cleaned_phone.apply(lambda x: ''.join(ch for ch in x if ch.isdigit())[:10])
        out['Phone'] = cleaned_phone
    else:
        out['Phone'] = pd.Series([''] * len(df))

    out['Department'] = get_series_or_empty(dept_col) if dept_col else pd.Series([''] * len(df))
    out['Year'] = get_series_or_empty(year_col) if year_col else pd.Series([''] * len(df))

    # Ensure dtypes are strings and trim whitespace
    for c in out_cols:
        out[c] = out[c].astype(str).fillna('').map(lambda v: v.strip())

    # Optionally drop completely empty rows (no ID, Name, Email)
    mask_nonempty = (out['ID'] != '') | (out['Name'] != '') | (out['Email'] != '')
    out = out[mask_nonempty].reset_index(drop=True)

    return out

# ----------------------------------------
# MongoDB helpers (only used when USE_MONGO is true)
# ----------------------------------------
def mongo_next_sequence(seq_name: str) -> int:
    if not USE_MONGO:
        return 0
    doc = mongo_db.counters.find_one_and_update(
        {'_id': seq_name},
        {'$inc': {'seq': 1}},
        upsert=True,
        return_document=True
    )
    return int(doc.get('seq', 1))

def mongo_student_to_dict(doc: dict) -> dict:
    return {
        'id': int(doc.get('id', 0)),
        'name': doc.get('name', ''),
        'email': doc.get('email', ''),
        'phone': doc.get('phone', ''),
        'department': doc.get('department', ''),
        'year': doc.get('year', ''),
        'created_at': (doc.get('created_at').isoformat() if doc.get('created_at') else None)
    }

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')  # Needed for session management

# Database configuration using environment variables
# Format: mysql+mysqlconnector://username:password@host:port/database
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
# IMPORTANT: read from standard env var name DB_PASSWORD. If your password has
# special characters (like @, :, /, #), SQLAlchemy URL will handle it if the
# value comes from the environment and you provide it raw in the connection
# string. For safety, users should avoid embedding passwords directly in
# code. Use a .env file instead.
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'exam_management')
DB_PORT = os.getenv('DB_PORT', '3306')

# Create the database URI
_encoded_password = quote_plus(DB_PASSWORD) if DB_PASSWORD else ''
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://{DB_USER}:{_encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Optional MongoDB configuration (activate by setting USE_MONGO=true)
USE_MONGO = os.getenv('USE_MONGO', 'false').strip().lower() == 'true'
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', DB_NAME)
mongo_client = None
mongo_db = None
if USE_MONGO:
    mongo_client = MongoClient(MONGO_URI)
    mongo_db = mongo_client[MONGO_DB_NAME]
    # Ensure indexes
    mongo_db.students.create_index([('email', ASCENDING)], unique=True)

# Make Mongo config available to ems_app
app.config['MONGO_URI'] = MONGO_URI
app.config['MONGO_DB_NAME'] = MONGO_DB_NAME
try:
    init_mongo(app)
except Exception:
    pass

# File upload configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Register additive v2 (Mongo-first) endpoints
app.register_blueprint(students_v2_bp)
app.register_blueprint(allocation_v2_bp)

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Database Models
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        """Hash and set the admin password"""
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password):
        """Check if provided password matches the hash"""
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    year = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Add this relationship:
    attendances = db.relationship('Attendance', back_populates='student', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'department': self.department,
            'year': self.year,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    exams = db.relationship('Exam', back_populates='staff', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'department': self.department,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Hall(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    room_number = db.Column(db.String(20))  # Add this field
    facilities = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    exams = db.relationship('Exam', back_populates='hall', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'capacity': self.capacity,
            'location': self.location,
            'room_number': self.room_number,  # Include this
            'facilities': self.facilities,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # Duration in minutes
    hall_id = db.Column(db.Integer, db.ForeignKey('hall.id'), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    year = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default='upcoming')  # New field: upcoming, ongoing, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    hall = db.relationship('Hall', back_populates='exams')
    staff = db.relationship('Staff', back_populates='exams')
    # Cascade delete for attendance records
    attendances = db.relationship('Attendance', back_populates='exam', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'subject': self.subject,
            'date': self.date.isoformat() if self.date else None,
            'time': self.time.isoformat() if self.time else None,
            'duration': self.duration,
            'hall_id': self.hall_id,
            'staff_id': self.staff_id,
            'department': self.department,
            'year': self.year,
            'status': self.status,  # Include status in dict
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'hall_name': self.hall.name if self.hall else None,
            'staff_name': self.staff.name if self.staff else None
        }

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # Present, Absent, Late
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    student = db.relationship('Student', back_populates='attendances')
    exam = db.relationship('Exam', back_populates='attendances')

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'exam_id': self.exam_id,
            'status': self.status,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'student_name': self.student.name if self.student else None,
            'exam_subject': self.exam.subject if self.exam else None
        }

# New domain models
class Subject(db.Model):
    __tablename__ = 'subject'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(50), nullable=True)
    year = db.Column(db.String(10), nullable=True)
    __table_args__ = (db.UniqueConstraint('code', 'title', name='uq_subject_code_title'),)

class StudentSubject(db.Model):
    __tablename__ = 'student_subject'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('student_id', 'subject_id', name='uq_student_subject'),)

class ExamSlot(db.Model):
    __tablename__ = 'exam_slot'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    session = db.Column(db.String(5), nullable=False)  # FN/AN
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    department = db.Column(db.String(50), nullable=True)
    year = db.Column(db.String(10), nullable=True)
    __table_args__ = (db.UniqueConstraint('date', 'session', 'subject_id', name='uq_exam_slot'),)

class HallSeat(db.Model):
    __tablename__ = 'hall_seat'
    id = db.Column(db.Integer, primary_key=True)
    exam_slot_id = db.Column(db.Integer, db.ForeignKey('exam_slot.id'), nullable=False)
    hall_id = db.Column(db.Integer, db.ForeignKey('hall.id'), nullable=False)
    seat_no = db.Column(db.Integer, nullable=False)  # 1..60
    desk_no = db.Column(db.Integer, nullable=False)  # 1..30
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('exam_slot_id', 'hall_id', 'seat_no', name='uq_slot_hall_seat'),)

class Faculty(db.Model):
    __tablename__ = 'faculty'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=True)
    phone = db.Column(db.String(15), nullable=True)
    department = db.Column(db.String(50), nullable=True)

class Invigilation(db.Model):
    __tablename__ = 'invigilation'
    id = db.Column(db.Integer, primary_key=True)
    exam_slot_id = db.Column(db.Integer, db.ForeignKey('exam_slot.id'), nullable=False)
    hall_id = db.Column(db.Integer, db.ForeignKey('hall.id'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    role = db.Column(db.String(20), default='Invigilator')
    __table_args__ = (db.UniqueConstraint('exam_slot_id', 'hall_id', 'faculty_id', name='uq_invigilation'),)

class BookletIssue(db.Model):
    __tablename__ = 'booklet_issue'
    id = db.Column(db.Integer, primary_key=True)
    exam_slot_id = db.Column(db.Integer, db.ForeignKey('exam_slot.id'), nullable=False)
    hall_id = db.Column(db.Integer, db.ForeignKey('hall.id'), nullable=False)
    issued = db.Column(db.Integer, default=0)
    used = db.Column(db.Integer, default=0)
    returned = db.Column(db.Integer, default=0)
    __table_args__ = (db.UniqueConstraint('exam_slot_id', 'hall_id', name='uq_booklet'),)

# Create tables
with app.app_context():
    db.create_all()
    
    # Create default admin user if it doesn't exist (SQL store)
    admin = Admin.query.filter_by(username='admin').first()
    if not admin:
        admin = Admin(username='admin')
        admin.set_password('admin123')  # Default password
        db.session.add(admin)
        db.session.commit()

# Routes
@app.route('/')
def index():
    # Check if admin is logged in
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and admin.check_password(password):
            session['admin_id'] = admin.id
            session['admin_username'] = admin.username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_id', None)
    session.pop('admin_username', None)
    return redirect(url_for('login'))

@app.route('/students')
def students():
    # Check if admin is logged in
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    # Try to load the most recently uploaded 16-column sheet view
    desired_cols = [
        'SNO','ENQ','Reg_No','Name of the Student','Prog & Year','CLASS CODE','year','Degree','Dept',
        'DEPT ORD','CLASS ORD','SUB ORD','SUB_CODE','SUB_TITLE','DATE','SESS'
    ]
    rows = []
    columns = desired_cols.copy()
    json_path = session.get('last_students_json')
    try:
        if json_path and os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                rows = json.load(f)
            if rows:
                # Keep only the columns present in data, preserving desired order
                present = [c for c in desired_cols if c in rows[0]]
                if present:
                    columns = present
    except Exception:
        rows = []
        columns = desired_cols.copy()

    # Build subject grouping summary: by (SUB_CODE, SUB_TITLE, DATE, SESS)
    subjects_map = {}
    for r in rows or []:
        key = (
            r.get('SUB_CODE', ''),
            r.get('SUB_TITLE', ''),
            r.get('DATE', ''),
            r.get('SESS', ''),
        )
        subjects_map[key] = subjects_map.get(key, 0) + 1
    subjects = [
        {
            'SUB_CODE': k[0],
            'SUB_TITLE': k[1],
            'DATE': k[2],
            'SESS': k[3],
            'TOTAL': v,
        }
        for k, v in sorted(subjects_map.items(), key=lambda x: (x[0][2], x[0][3], x[0][0], x[0][1]))
    ]

    # Calculate total students count
    total_uploaded = len(rows) if rows else 0
    total_db = len(Student.query.all()) if not USE_MONGO else len(list(mongo_db.students.find()))
    total_students = total_uploaded + total_db

    return render_template('students.html', columns=columns, rows=rows, subjects=subjects, total_students=total_students)

@app.route('/staff')
def staff():
    # Check if admin is logged in
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    return render_template('staff.html')

@app.route('/halls')
def halls():
    # Check if admin is logged in
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    return render_template('halls.html')

@app.route('/exams')
def exams():
    # Check if admin is logged in
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    return render_template('exams.html')

@app.route('/hall_tickets')
def hall_tickets():
    # Check if admin is logged in
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    return render_template('hall_tickets.html')

@app.route('/reports')
def reports():
    # Check if admin is logged in
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    return render_template('reports.html')

@app.route('/attendance')
def attendance():
    # Check if admin is logged in
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    return render_template('attendance.html')

@app.route('/uploaded_students')
def uploaded_students():
    # Check if admin is logged in
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    # Fetch all students from database
    students = Student.query.all()
    return render_template('uploaded_students.html', students=students)
@app.route('/api/students', methods=['GET'])
def get_students():
    try:
        if USE_MONGO:
            docs = list(mongo_db.students.find({}, {'_id': 0}))
            return jsonify([mongo_student_to_dict(d) for d in docs])
        else:
            students = Student.query.all()
            return jsonify([student.to_dict() for student in students])
    except Exception as e:
        return jsonify({'error': 'Failed to fetch students'}), 500

@app.route('/api/students', methods=['POST'])
def create_student():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'email', 'phone', 'department', 'year']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, data['email']):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate phone number format (10 digits)
        phone_pattern = r'^\d{10}$'
        if not re.match(phone_pattern, data['phone']):
            return jsonify({'error': 'Phone number must be 10 digits'}), 400
        
        if USE_MONGO:
            try:
                next_id = mongo_next_sequence('students')
                doc = {
                    'id': next_id,
                    'name': data['name'],
                    'email': data['email'],
                    'phone': data['phone'],
                    'department': data['department'],
                    'year': data['year'],
                    'created_at': datetime.utcnow()
                }
                mongo_db.students.insert_one(doc)
                return jsonify(mongo_student_to_dict(doc)), 201
            except DuplicateKeyError:
                return jsonify({'error': 'Student with this email already exists'}), 400
        else:
            existing_student = Student.query.filter_by(email=data['email']).first()
            if existing_student:
                return jsonify({'error': 'Student with this email already exists'}), 400
            student = Student(
                name=data['name'],
                email=data['email'],
                phone=data['phone'],
                department=data['department'],
                year=data['year']
            )
            db.session.add(student)
            db.session.commit()
            return jsonify(student.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create student'}), 500

@app.route('/api/students/<int:id>', methods=['GET'])
def get_student(id):
    try:
        if USE_MONGO:
            doc = mongo_db.students.find_one({'id': id}, {'_id': 0})
            if not doc:
                return jsonify({'error': 'Student not found'}), 404
            return jsonify(mongo_student_to_dict(doc))
        else:
            student = Student.query.get_or_404(id)
            return jsonify(student.to_dict())
    except Exception as e:
        return jsonify({'error': 'Student not found'}), 404

@app.route('/api/students/<int:id>', methods=['PUT'])
def update_student(id):
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'email', 'phone', 'department', 'year']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, data['email']):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate phone number format (10 digits)
        phone_pattern = r'^\d{10}$'
        if not re.match(phone_pattern, data['phone']):
            return jsonify({'error': 'Phone number must be 10 digits'}), 400
        
        if USE_MONGO:
            other = mongo_db.students.find_one({'email': data['email'], 'id': {'$ne': id}})
            if other:
                return jsonify({'error': 'Student with this email already exists'}), 400
            res = mongo_db.students.find_one_and_update(
                {'id': id},
                {'$set': {
                    'name': data['name'],
                    'email': data['email'],
                    'phone': data['phone'],
                    'department': data['department'],
                    'year': data['year']
                }},
                return_document=True
            )
            if not res:
                return jsonify({'error': 'Student not found'}), 404
            return jsonify(mongo_student_to_dict(res))
        else:
            student = Student.query.get_or_404(id)
            existing_student = Student.query.filter_by(email=data['email']).first()
            if existing_student and existing_student.id != id:
                return jsonify({'error': 'Student with this email already exists'}), 400
            student.name = data['name']
            student.email = data['email']
            student.phone = data['phone']
            student.department = data['department']
            student.year = data['year']
            db.session.commit()
            return jsonify(student.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update student'}), 500

@app.route('/api/students/<int:id>', methods=['DELETE'])
def delete_student(id):
    try:
        if USE_MONGO:
            res = mongo_db.students.delete_one({'id': id})
            if res.deleted_count == 0:
                return jsonify({'error': 'Student not found'}), 404
            return '', 204
        else:
            student = Student.query.get_or_404(id)
            # Delete related records first to satisfy foreign key constraints
            Attendance.query.filter_by(student_id=id).delete()
            HallSeat.query.filter_by(student_id=id).delete()
            StudentSubject.query.filter_by(student_id=id).delete()
            db.session.delete(student)
            db.session.commit()
            return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete student'}), 500

# Staff API Routes
@app.route('/api/staff', methods=['GET'])
def get_staff():
    try:
        staff = Staff.query.all()
        return jsonify([staff_member.to_dict() for staff_member in staff])
    except Exception as e:
        return jsonify({'error': 'Failed to fetch staff'}), 500

@app.route('/api/staff', methods=['POST'])
def create_staff():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'email', 'phone', 'department', 'role']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, data['email']):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate phone number format (10 digits)
        phone_pattern = r'^\d{10}$'
        if not re.match(phone_pattern, data['phone']):
            return jsonify({'error': 'Phone number must be 10 digits'}), 400
        
        # Check if staff with this email already exists
        existing_staff = Staff.query.filter_by(email=data['email']).first()
        if existing_staff:
            return jsonify({'error': 'Staff with this email already exists'}), 400
        
        staff = Staff(
            name=data['name'],
            email=data['email'],
            phone=data['phone'],
            department=data['department'],
            role=data['role']
        )
        db.session.add(staff)
        db.session.commit()
        return jsonify(staff.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create staff'}), 500

@app.route('/api/staff/<int:id>', methods=['GET'])
def get_staff_member(id):
    try:
        staff = Staff.query.get_or_404(id)
        return jsonify(staff.to_dict())
    except Exception as e:
        return jsonify({'error': 'Staff member not found'}), 404

@app.route('/api/staff/<int:id>', methods=['PUT'])
def update_staff(id):
    try:
        staff = Staff.query.get_or_404(id)
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'email', 'phone', 'department', 'role']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, data['email']):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate phone number format (10 digits)
        phone_pattern = r'^\d{10}$'
        if not re.match(phone_pattern, data['phone']):
            return jsonify({'error': 'Phone number must be 10 digits'}), 400
        
        # Check if another staff with this email already exists
        existing_staff = Staff.query.filter_by(email=data['email']).first()
        if existing_staff and existing_staff.id != id:
            return jsonify({'error': 'Staff with this email already exists'}), 400
        
        staff.name = data['name']
        staff.email = data['email']
        staff.phone = data['phone']
        staff.department = data['department']
        staff.role = data['role']
        db.session.commit()
        return jsonify(staff.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update staff'}), 500

@app.route('/api/staff/<int:id>', methods=['DELETE'])
def delete_staff(id):
    try:
        staff = Staff.query.get_or_404(id)
        db.session.delete(staff)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete staff'}), 500

# Hall API Routes
@app.route('/api/halls', methods=['GET'])
def get_halls():
    try:
        halls = Hall.query.all()
        return jsonify([hall.to_dict() for hall in halls])
    except Exception as e:
        return jsonify({'error': 'Failed to fetch halls'}), 500

@app.route('/api/halls', methods=['POST'])
def create_hall():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'capacity', 'location']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate capacity is a positive integer
        try:
            capacity = int(data['capacity'])
            if capacity <= 0:
                return jsonify({'error': 'Capacity must be a positive integer'}), 400
        except ValueError:
            return jsonify({'error': 'Capacity must be a valid integer'}), 400
        
        # Check if hall with this name already exists
        existing_hall = Hall.query.filter_by(name=data['name']).first()
        if existing_hall:
            return jsonify({'error': 'Hall with this name already exists'}), 400
        
        hall = Hall(
            name=data['name'],
            capacity=capacity,
            location=data['location'],
            facilities=data.get('facilities', '')
        )
        db.session.add(hall)
        db.session.commit()
        return jsonify(hall.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create hall'}), 500

@app.route('/api/halls/<int:id>', methods=['GET'])
def get_hall(id):
    try:
        hall = Hall.query.get_or_404(id)
        return jsonify(hall.to_dict())
    except Exception as e:
        return jsonify({'error': 'Hall not found'}), 404

@app.route('/api/halls/<int:id>', methods=['PUT'])
def update_hall(id):
    try:
        hall = Hall.query.get_or_404(id)
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'capacity', 'location']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate capacity is a positive integer
        try:
            capacity = int(data['capacity'])
            if capacity <= 0:
                return jsonify({'error': 'Capacity must be a positive integer'}), 400
        except ValueError:
            return jsonify({'error': 'Capacity must be a valid integer'}), 400
        
        # Check if another hall with this name already exists
        existing_hall = Hall.query.filter_by(name=data['name']).first()
        if existing_hall and existing_hall.id != id:
            return jsonify({'error': 'Hall with this name already exists'}), 400
        
        hall.name = data['name']
        hall.capacity = capacity
        hall.location = data['location']
        hall.facilities = data.get('facilities', '')
        db.session.commit()
        return jsonify(hall.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update hall'}), 500

@app.route('/api/halls/<int:id>', methods=['DELETE'])
def delete_hall(id):
    try:
        hall = Hall.query.get_or_404(id)
        db.session.delete(hall)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete hall'}), 500

# Exam API Routes
@app.route('/api/exams', methods=['GET'])
def get_exams():
    try:
        exams = Exam.query.all()
        return jsonify([exam.to_dict() for exam in exams])
    except Exception as e:
        return jsonify({'error': 'Failed to fetch exams'}), 500




@app.route('/api/exams', methods=['POST'])
def create_exam():
    try:
        data = request.get_json()
        print(f"Received exam data: {data}")  # Debug output
        
        # Validate required fields
        required_fields = ['subject', 'date', 'time', 'duration', 'hall_id', 'staff_id', 'department', 'year']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate duration is a positive integer
        try:
            duration = int(data['duration'])
            if duration <= 0:
                return jsonify({'error': 'Duration must be a positive integer'}), 400
        except ValueError:
            return jsonify({'error': 'Duration must be a valid integer'}), 400
        
        # Validate date and time format
        try:
            exam_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            exam_time = datetime.strptime(data['time'], '%H:%M').time()
        except ValueError:
            return jsonify({'error': 'Invalid date or time format. Use YYYY-MM-DD for date and HH:MM for time'}), 400
        
        # Check if exam date is in the future
        from datetime import date
        if exam_date < date.today():
            return jsonify({'error': 'Exam date must be in the future'}), 400
        
        # Check if hall exists
        hall = Hall.query.get(data['hall_id'])
        if not hall:
            return jsonify({'error': 'Hall not found'}), 400
        
        # Check if staff exists
        staff = Staff.query.get(data['staff_id'])
        if not staff:
            return jsonify({'error': 'Staff not found'}), 400
        
        # Check for scheduling conflicts (same hall at same time)
        conflicting_exam = Exam.query.filter(
            Exam.hall_id == data['hall_id'],
            Exam.date == exam_date,
            Exam.time == exam_time
        ).first()
        
        if conflicting_exam:
            return jsonify({'error': 'Hall is already booked for this date and time'}), 400
        
        exam = Exam(
            subject=data['subject'],
            date=exam_date,
            time=exam_time,
            duration=duration,
            hall_id=data['hall_id'],
            staff_id=data['staff_id'],
            department=data['department'],
            year=data['year'],
            status=data.get('status', 'upcoming')  # Add this line
        )
        db.session.add(exam)
        db.session.commit()
        return jsonify(exam.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create exam: {str(e)}'}), 500



@app.route('/api/exams/<int:id>', methods=['GET'])
def get_exam(id):
    try:
        exam = Exam.query.get_or_404(id)
        return jsonify(exam.to_dict())
    except Exception as e:
        return jsonify({'error': 'Exam not found'}), 404




@app.route('/api/exams/<int:id>', methods=['PUT'])
def update_exam(id):
    try:
        exam = Exam.query.get_or_404(id)
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['subject', 'date', 'time', 'duration', 'hall_id', 'staff_id', 'department', 'year']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate duration is a positive integer
        try:
            duration = int(data['duration'])
            if duration <= 0:
                return jsonify({'error': 'Duration must be a positive integer'}), 400
        except ValueError:
            return jsonify({'error': 'Duration must be a valid integer'}), 400
        
        # Validate date and time format
        try:
            exam_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            exam_time = datetime.strptime(data['time'], '%H:%M').time()
        except ValueError:
            return jsonify({'error': 'Invalid date or time format. Use YYYY-MM-DD for date and HH:MM for time'}), 400
        
        # Check if exam date is in the future
        from datetime import date
        if exam_date < date.today():
            return jsonify({'error': 'Exam date must be in the future'}), 400
        
        # Check if hall exists
        hall = Hall.query.get(data['hall_id'])
        if not hall:
            return jsonify({'error': 'Hall not found'}), 400
        
        # Check if staff exists
        staff = Staff.query.get(data['staff_id'])
        if not staff:
            return jsonify({'error': 'Staff not found'}), 400
        
        # Check for scheduling conflicts (same hall at same time, excluding current exam)
        conflicting_exam = Exam.query.filter(
            Exam.hall_id == data['hall_id'],
            Exam.date == exam_date,
            Exam.time == exam_time,
            Exam.id != id
        ).first()
        
        if conflicting_exam:
            return jsonify({'error': 'Hall is already booked for this date and time'}), 400
        
        exam.subject = data['subject']
        exam.date = exam_date
        exam.time = exam_time
        exam.duration = duration
        exam.hall_id = data['hall_id']
        exam.staff_id = data['staff_id']
        exam.department = data['department']
        exam.year = data['year']
        exam.status = data.get('status', exam.status)  # Add this line
        db.session.commit()
        return jsonify(exam.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update exam: {str(e)}'}), 500




@app.route('/api/exams/<int:id>', methods=['DELETE'])
def delete_exam(id):
    try:
        exam = Exam.query.get_or_404(id)
        db.session.delete(exam)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete exam'}), 500



# Attendance API Routes
@app.route('/api/attendances', methods=['GET'])
def get_attendances():
    try:
        attendances = Attendance.query.all()
        return jsonify([attendance.to_dict() for attendance in attendances])
    except Exception as e:
        return jsonify({'error': 'Failed to fetch attendances'}), 500




@app.route('/api/attendances', methods=['POST'])
def create_attendance():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['student_id', 'exam_id', 'status']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate status
        valid_statuses = ['Present', 'Absent', 'Late']
        if data['status'] not in valid_statuses:
            return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
        
        # Check if student exists
        student = Student.query.get(data['student_id'])
        if not student:
            return jsonify({'error': 'Student not found'}), 400
        
        # Check if exam exists
        exam = Exam.query.get(data['exam_id'])
        if not exam:
            return jsonify({'error': 'Exam not found'}), 400
        
        # Check if attendance record already exists
        existing_attendance = Attendance.query.filter_by(student_id=data['student_id'], exam_id=data['exam_id']).first()
        if existing_attendance:
            return jsonify({'error': 'Attendance record already exists for this student and exam'}), 400
        
        attendance = Attendance(
            student_id=data['student_id'],
            exam_id=data['exam_id'],
            status=data['status'],
            remarks=data.get('remarks', '')
        )
        db.session.add(attendance)
        db.session.commit()
        return jsonify(attendance.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create attendance: {str(e)}'}), 500




@app.route('/api/attendances/<int:id>', methods=['GET'])
def get_attendance(id):
    try:
        attendance = Attendance.query.get_or_404(id)
        return jsonify(attendance.to_dict())
    except Exception as e:
        return jsonify({'error': 'Attendance record not found'}), 404



@app.route('/api/attendances/<int:id>', methods=['PUT'])
def update_attendance(id):
    try:
        attendance = Attendance.query.get_or_404(id)
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['student_id', 'exam_id', 'status']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate status
        valid_statuses = ['Present', 'Absent', 'Late']
        if data['status'] not in valid_statuses:
            return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
        
        # Check if student exists
        student = Student.query.get(data['student_id'])
        if not student:
            return jsonify({'error': 'Student not found'}), 400
        
        # Check if exam exists
        exam = Exam.query.get(data['exam_id'])
        if not exam:
            return jsonify({'error': 'Exam not found'}), 400
        
        attendance.student_id = data['student_id']
        attendance.exam_id = data['exam_id']
        attendance.status = data['status']
        attendance.remarks = data.get('remarks', '')
        db.session.commit()
        return jsonify(attendance.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update attendance: {str(e)}'}), 500



@app.route('/api/attendances/<int:id>', methods=['DELETE'])
def delete_attendance(id):
    try:
        attendance = Attendance.query.get_or_404(id)
        db.session.delete(attendance)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete attendance'}), 500




# File Upload Routes
@app.route('/api/upload/students', methods=['POST'])
def upload_students():
    # Check if admin is logged in
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            # Opportunistically persist a 16-column display JSON for the Students page
            try:
                raw = None
                if filename.endswith('.csv'):
                    raw = pd.read_csv(file_path, dtype=str)
                elif filename.endswith(('.xlsx', '.xls')):
                    raw = pd.read_excel(file_path, dtype=str)
                if raw is not None and len(raw.columns) > 0:
                    desired_cols = [
                        'SNO','ENQ','Reg_No','Name of the Student','Prog & Year','CLASS CODE','year','Degree','Dept',
                        'DEPT ORD','CLASS ORD','SUB ORD','SUB_CODE','SUB_TITLE','DATE','SESS'
                    ]
                    cols_lower = {str(c).strip().lower(): c for c in raw.columns}
                    def get_src(name: str):
                        keys = [name,
                                name.replace('_',' '),
                                name.replace('&','and'),
                                name.replace('  ',' ')]
                        for k in keys:
                            lk = k.strip().lower()
                            if lk in cols_lower:
                                return cols_lower[lk]
                        return None
                    data = {}
                    for dc in desired_cols:
                        src = get_src(dc)
                        if src:
                            data[dc] = raw[src].astype(str)
                        else:
                            data[dc] = ""
                    display_df2 = pd.DataFrame(data, columns=desired_cols).fillna("")
                    json_path2 = os.path.join(app.config['UPLOAD_FOLDER'], 'last_students.json')
                    display_df2.to_json(json_path2, orient='records', force_ascii=False)
                    session['last_students_json'] = json_path2
            except Exception:
                pass

            # Transform to standardized columns
            std_df = transform_excel(file_path)

            saved_count = 0
            errors = []

            for index, row in std_df.iterrows():
                try:
                    id_val = str(row['ID']).strip()
                    name_val = str(row['Name']).strip()
                    email_val = str(row['Email']).strip()
                    phone_val = str(row['Phone']).strip()
                    dept_val = str(row['Department']).strip()
                    year_val = str(row['Year']).strip()

                    # If email missing but ID present, derive pseudo email; else if both missing, skip
                    if not email_val:
                        if id_val:
                            email_val = f"{id_val}@example.edu"
                        else:
                            raise ValueError('Missing Email and ID')

                    # If phone missing, keep empty string (as per requirement)
                    # Ensure phone has only digits (optional cleanup)
                    phone_val = ''.join(ch for ch in phone_val if ch.isdigit())[:10] if phone_val else ''

                    if not name_val:
                        raise ValueError('Missing Name')

                    if USE_MONGO:
                        # Upsert by email
                        doc = {
                            'name': name_val,
                            'email': email_val,
                            'phone': phone_val,
                            'department': dept_val,
                            'year': year_val
                        }
                        existing = mongo_db.students.find_one({'email': email_val})
                        if existing:
                            mongo_db.students.update_one({'email': email_val}, {'$set': doc})
                        else:
                            doc['id'] = mongo_next_sequence('students')
                            doc['created_at'] = datetime.utcnow()
                            mongo_db.students.insert_one(doc)
                    else:
                        existing_student = Student.query.filter_by(email=email_val).first()
                        if existing_student:
                            existing_student.name = name_val
                            existing_student.phone = phone_val
                            existing_student.department = dept_val
                            existing_student.year = year_val
                        else:
                            student = Student(
                                name=name_val,
                                email=email_val,
                                phone=phone_val,
                                department=dept_val,
                                year=year_val
                            )
                            db.session.add(student)

                    saved_count += 1
                except Exception as e:
                    errors.append(f"Row {index + 1}: {str(e)}")

            if not USE_MONGO:
                db.session.commit()

            # Clean up uploaded file
            os.remove(file_path)

            return jsonify({
                'message': f'Successfully processed {int(saved_count)} students',
                'processed_rows': int(len(std_df)),
                'saved_students': int(saved_count),
                'errors': errors
            }), 200

        except Exception as e:
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    
    return jsonify({'error': 'File upload failed'}), 500



@app.route('/api/upload/staff', methods=['POST'])
def upload_staff():
    # Check if admin is logged in
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            # Determine file type and read accordingly
            if filename.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            else:
                return jsonify({'error': 'Unsupported file format'}), 400
            
            # Process the data and save to database
            saved_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # Check if staff already exists
                    existing_staff = Staff.query.filter_by(email=row['email']).first()
                    if existing_staff:
                        # Update existing staff
                        existing_staff.name = row['name']
                        existing_staff.phone = row['phone']
                        existing_staff.department = row['department']
                        existing_staff.role = row['role']
                    else:
                        # Create new staff
                        staff = Staff(
                            name=row['name'],
                            email=row['email'],
                            phone=row['phone'],
                            department=row['department'],
                            role=row['role']
                        )
                        db.session.add(staff)
                    
                    saved_count += 1
                except Exception as e:
                    errors.append(f"Row {index + 1}: {str(e)}")
            
            db.session.commit()
            
            # Clean up uploaded file
            os.remove(file_path)
            
            return jsonify({
                'message': f'Successfully processed {saved_count} staff members',
                'errors': errors
            }), 200
            
        except Exception as e:
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    
    return jsonify({'error': 'File upload failed'}), 500




@app.route('/api/import/excel', methods=['POST'])
def import_excel():
    # Import pipeline for headers: reg_no,name,department,year,subject_code,subject_title,exam_date,session,hall_no?,seat_no?
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        df.columns = [str(c).strip().lower() for c in df.columns]
        required = ['reg_no', 'name', 'department', 'year', 'subject_code', 'subject_title', 'exam_date', 'session']
        missing = [c for c in required if c not in df.columns]
        if missing:
            return jsonify({'error': f'Missing columns: {", ".join(missing)}'}), 400

        from datetime import datetime as _dt

        created_students = 0
        created_subjects = 0
        created_slots = 0
        created_links = 0
        created_seats = 0

        # Cache lookups
        subj_cache = {}
        student_cache = {}

        for _, row in df.iterrows():
            reg = str(row['reg_no']).strip()
            sname = str(row['name']).strip()
            dept = str(row['department']).strip()
            year = str(row['year']).strip()
            scode = str(row['subject_code']).strip()
            stitle = str(row['subject_title']).strip()
            date_val = row['exam_date']
            sess = str(row['session']).strip().upper()
            hall_no = str(row['hall_no']).strip() if 'hall_no' in df.columns and pd.notna(row['hall_no']) else None
            seat_no = int(row['seat_no']) if 'seat_no' in df.columns and pd.notna(row['seat_no']) else None

            # Student
            email = f"{reg}@example.edu"
            student = student_cache.get(email) or Student.query.filter_by(email=email).first()
            if not student:
                student = Student(name=sname, email=email, phone='0000000000', department=dept, year=year)
                db.session.add(student)
                db.session.flush()
                created_students += 1
                student_cache[email] = student

            # Subject
            subj_key = (scode, stitle)
            subject = subj_cache.get(subj_key) or Subject.query.filter_by(code=scode, title=stitle).first()
            if not subject:
                subject = Subject(code=scode, title=stitle, department=dept, year=year)
                db.session.add(subject)
                db.session.flush()
                created_subjects += 1
                subj_cache[subj_key] = subject

            # StudentSubject link
            link = StudentSubject.query.filter_by(student_id=student.id, subject_id=subject.id).first()
            if not link:
                link = StudentSubject(student_id=student.id, subject_id=subject.id)
                db.session.add(link)
                created_links += 1

            # ExamSlot
            try:
                if isinstance(date_val, str):
                    ex_date = _dt.strptime(date_val.strip(), '%Y-%m-%d').date() if '-' in date_val else _dt.strptime(date_val.strip(), '%d-%m-%Y').date()
                else:
                    ex_date = pd.to_datetime(date_val).date()
            except Exception:
                return jsonify({'error': f'Invalid exam_date: {date_val}'}), 400

            slot = ExamSlot.query.filter_by(date=ex_date, session=sess, subject_id=subject.id).first()
            if not slot:
                slot = ExamSlot(date=ex_date, session=sess, subject_id=subject.id, department=dept, year=year)
                db.session.add(slot)
                db.session.flush()
                created_slots += 1

            # Optional pre-assigned seating
            if hall_no and seat_no:
                hall = Hall.query.filter((Hall.name == hall_no) | (Hall.room_number == hall_no)).first()
                if hall:
                    desk_no = ((seat_no - 1) // 2) + 1
                    if 1 <= seat_no <= 60:
                        existing = HallSeat.query.filter_by(exam_slot_id=slot.id, hall_id=hall.id, seat_no=seat_no).first()
                        if not existing:
                            hs = HallSeat(exam_slot_id=slot.id, hall_id=hall.id, seat_no=seat_no, desk_no=desk_no, student_id=student.id)
                            db.session.add(hs)
                            created_seats += 1

        db.session.commit()
        os.remove(file_path)
        return jsonify({
            'created_students': created_students,
            'created_subjects': created_subjects,
            'created_exam_slots': created_slots,
            'created_student_subject_links': created_links,
            'created_preassigned_seats': created_seats
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Import failed: {str(e)}'}), 500
    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass


@app.route('/api/allocate', methods=['POST'])
def allocate_halls():
    # Body: { date: YYYY-MM-DD, session: FN|AN, hall_ids: [..] }
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    try:
        from datetime import datetime as _dt
        date_str = data.get('date')
        sess = (data.get('session') or '').upper()
        hall_ids = data.get('hall_ids') or []
        if not date_str or not sess or not hall_ids:
            return jsonify({'error': 'date, session, hall_ids are required'}), 400
        ex_date = _dt.strptime(date_str, '%Y-%m-%d').date()

        halls = Hall.query.filter(Hall.id.in_(hall_ids)).order_by(Hall.capacity.desc()).all()
        if not halls:
            return jsonify({'error': 'No halls found'}), 400

        # For each slot on date/session, gather students needing seats
        slots = ExamSlot.query.filter_by(date=ex_date, session=sess).all()
        result = []
        for slot in slots:
            # Find students registered to this subject
            students = (db.session.query(Student)
                        .join(StudentSubject, Student.id == StudentSubject.student_id)
                        .filter(StudentSubject.subject_id == slot.subject_id)
                        .all())

            # Exclude already seated
            seated_ids = set(s.student_id for s in HallSeat.query.filter_by(exam_slot_id=slot.id).all())
            queue = [s for s in students if s.id not in seated_ids]

            # Anti-malpractice: interleave by (department, year)
            from collections import defaultdict, deque
            groups = defaultdict(list)
            for s in queue:
                groups[(s.department, s.year)].append(s)
            # Sort groups by size desc and make deques
            group_deques = [deque(v) for k,v in sorted(groups.items(), key=lambda kv: -len(kv[1]))]

            def next_student(idx=[0]):
                # round-robin across groups
                for _ in range(len(group_deques)):
                    g = group_deques[idx[0] % len(group_deques)]
                    idx[0] += 1
                    if g:
                        return g.popleft()
                return None

            # Allocate across halls
            allocations = []
            for hall in halls:
                capacity = min(hall.capacity or 60, 60)  # cap at 60 per requirement
                seats = []
                for seat_no in range(1, capacity + 1):
                    student = next_student()
                    if not student:
                        break
                    desk_no = ((seat_no - 1) // 2) + 1
                    seats.append((seat_no, desk_no, student))
                # Persist
                for seat_no, desk_no, student in seats:
                    hs = HallSeat(exam_slot_id=slot.id, hall_id=hall.id, seat_no=seat_no, desk_no=desk_no, student_id=student.id)
                    db.session.add(hs)
                allocations.append({'hall_id': hall.id, 'allocated': len(seats)})

            result.append({'exam_slot_id': slot.id, 'subject_id': slot.subject_id, 'allocations': allocations})

        db.session.commit()
        return jsonify({'message': 'Allocation completed', 'slots': result})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Allocation failed: {str(e)}'}), 500


@app.route('/hall_ticket_pdf/<int:student_id>')
def hall_ticket_pdf(student_id: int):
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    date_str = request.args.get('date')
    sess = (request.args.get('session') or '').upper()
    if not date_str or not sess:
        return render_template('hall_ticket_error.html', message='date and session are required')
    from datetime import datetime as _dt
    try:
        ex_date = _dt.strptime(date_str, '%Y-%m-%d').date()
    except Exception:
        return render_template('hall_ticket_error.html', message='Invalid date format')

    student = Student.query.get_or_404(student_id)
    # Find all seats for this student at date/session
    records = (db.session.query(HallSeat, ExamSlot, Hall, Subject)
               .join(ExamSlot, HallSeat.exam_slot_id == ExamSlot.id)
               .join(Hall, HallSeat.hall_id == Hall.id)
               .join(Subject, ExamSlot.subject_id == Subject.id)
               .filter(HallSeat.student_id == student_id, ExamSlot.date == ex_date, ExamSlot.session == sess)
               .all())

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    # Header
    c.setFont('Helvetica-Bold', 14)
    c.drawString(20*mm, (H-20*mm), 'HALL TICKET')
    c.setFont('Helvetica', 10)
    c.drawString(20*mm, (H-26*mm), f"Name: {student.name}")
    reg = student.email.split('@')[0] if student.email else ''
    c.drawString(20*mm, (H-32*mm), f"Reg No: {reg}")
    c.drawString(20*mm, (H-38*mm), f"Department: {student.department}  Year: {student.year}")
    c.drawString(20*mm, (H-44*mm), f"Date: {ex_date.isoformat()}  Session: {sess}")

    # QR code
    qr = qrcode.make(f"{reg}|{ex_date}|{sess}")
    qr_buf = BytesIO()
    qr.save(qr_buf, format='PNG')
    qr_buf.seek(0)
    c.drawImage(qr_buf, (W-40*mm), (H-50*mm), 20*mm, 20*mm, preserveAspectRatio=True, mask='auto')

    y = H - 60*mm
    c.setFont('Helvetica-Bold', 10)
    c.drawString(20*mm, y, 'Paper Code')
    c.drawString(60*mm, y, 'Title')
    c.drawString(150*mm, y, 'Hall/Seat')
    y -= 6*mm
    c.setFont('Helvetica', 10)
    for hs, slot, hall, subj in records:
        c.drawString(20*mm, y, subj.code)
        c.drawString(60*mm, y, (subj.title[:50] + ('...' if len(subj.title) > 50 else '')))
        c.drawString(150*mm, y, f"{hall.name} / {hs.seat_no}")
        y -= 6*mm
        if y < 20*mm:
            c.showPage(); y = H - 20*mm

    c.showPage()
    c.save()
    pdf = buf.getvalue()
    buf.close()
    return Response(pdf, mimetype='application/pdf', headers={'Content-Disposition': 'inline; filename=hall_ticket.pdf'})


@app.route('/attendance_sheet_pdf')
def attendance_sheet_pdf():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    date_str = request.args.get('date')
    sess = (request.args.get('session') or '').upper()
    hall_id = request.args.get('hall_id', type=int)
    if not date_str or not sess or not hall_id:
        return render_template('hall_ticket_error.html', message='date, session, hall_id are required')
    from datetime import datetime as _dt
    ex_date = _dt.strptime(date_str, '%Y-%m-%d').date()

    hall = Hall.query.get_or_404(hall_id)
    records = (db.session.query(HallSeat, ExamSlot, Student, Subject)
               .join(ExamSlot, HallSeat.exam_slot_id == ExamSlot.id)
               .join(Student, HallSeat.student_id == Student.id)
               .join(Subject, ExamSlot.subject_id == Subject.id)
               .filter(ExamSlot.date == ex_date, ExamSlot.session == sess, HallSeat.hall_id == hall_id)
               .order_by(HallSeat.seat_no.asc())
               .all())

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    c.setFont('Helvetica-Bold', 12)
    c.drawString(20*mm, (H-20*mm), f"Attendance Sheet - {hall.name}  {ex_date} {sess}")
    y = H - 30*mm
    c.setFont('Helvetica-Bold', 10)
    c.drawString(20*mm, y, 'Seat')
    c.drawString(35*mm, y, 'Reg No')
    c.drawString(70*mm, y, 'Name')
    c.drawString(150*mm, y, 'Sign')
    y -= 6*mm
    c.setFont('Helvetica', 10)
    for hs, slot, stu, subj in records:
        reg = stu.email.split('@')[0] if stu.email else ''
        c.drawString(20*mm, y, str(hs.seat_no))
        c.drawString(35*mm, y, reg)
        c.drawString(70*mm, y, (stu.name[:40] + ('...' if len(stu.name) > 40 else '')))
        c.line(150*mm, y-1*mm, (W-20*mm), y-1*mm)
        y -= 7*mm
        if y < 20*mm:
            c.showPage(); y = H - 20*mm
    c.showPage(); c.save()
    pdf = buf.getvalue(); buf.close()
    return Response(pdf, mimetype='application/pdf', headers={'Content-Disposition': 'inline; filename=attendance.pdf'})


@app.route('/api/export/halltickets_zip', methods=['GET'])
def export_halltickets_zip():
    # Params: date=YYYY-MM-DD, session=FN|AN, optional subject_code, hall_id
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    date_str = request.args.get('date')
    sess = (request.args.get('session') or '').upper()
    subject_code = request.args.get('subject_code')
    hall_id = request.args.get('hall_id', type=int)
    if not date_str or not sess:
        return jsonify({'error': 'date and session required'}), 400
    from datetime import datetime as _dt
    try:
        ex_date = _dt.strptime(date_str, '%Y-%m-%d').date()
    except Exception:
        return jsonify({'error': 'Invalid date'}), 400

    # Build query of (student, hallseat, hall, subject) at date/session
    q = (db.session.query(Student, HallSeat, Hall, Subject)
         .join(HallSeat, HallSeat.student_id == Student.id)
         .join(ExamSlot, HallSeat.exam_slot_id == ExamSlot.id)
         .join(Hall, HallSeat.hall_id == Hall.id)
         .join(Subject, ExamSlot.subject_id == Subject.id)
         .filter(ExamSlot.date == ex_date, ExamSlot.session == sess))
    if subject_code:
        q = q.filter(Subject.code == subject_code)
    if hall_id:
        q = q.filter(Hall.id == hall_id)

    records = q.all()
    if not records:
        return jsonify({'error': 'No tickets found'}), 404

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    with zipfile.ZipFile(tmp.name, 'w', zipfile.ZIP_DEFLATED) as zf:
        for student, hs, hall, subj in records:
            reg = student.email.split('@')[0] if student.email else str(student.id)
            # Generate single-page PDF ticket buffer
            buf = BytesIO(); c = canvas.Canvas(buf, pagesize=A4); W,H = A4
            c.setFont('Helvetica-Bold', 14)
            c.drawString(20*mm, (H-20*mm), 'HALL TICKET')
            c.setFont('Helvetica', 10)
            c.drawString(20*mm, (H-26*mm), f"Name: {student.name}")
            c.drawString(20*mm, (H-32*mm), f"Reg No: {reg}")
            c.drawString(20*mm, (H-38*mm), f"Department: {student.department}  Year: {student.year}")
            c.drawString(20*mm, (H-44*mm), f"Date: {ex_date.isoformat()}  Session: {sess}")
            # QR
            qr = qrcode.make(f"{reg}|{ex_date}|{sess}|{subj.code}")
            qb = BytesIO(); qr.save(qb, format='PNG'); qb.seek(0)
            c.drawImage(qb, (W-40*mm), (H-50*mm), 20*mm, 20*mm, preserveAspectRatio=True, mask='auto')
            # Row
            y = H - 60*mm; c.setFont('Helvetica-Bold', 10)
            c.drawString(20*mm, y, 'Paper Code'); c.drawString(60*mm, y, 'Title'); c.drawString(150*mm, y, 'Hall/Seat')
            y -= 6*mm; c.setFont('Helvetica', 10)
            c.drawString(20*mm, y, subj.code)
            title = (subj.title[:50] + ('...' if len(subj.title) > 50 else ''))
            c.drawString(60*mm, y, title)
            c.drawString(150*mm, y, f"{hall.name} / {hs.seat_no}")
            c.showPage(); c.save(); pdf = buf.getvalue(); buf.close()
            fname = f"{reg}_{ex_date.isoformat()}_{sess}.pdf"
            zf.writestr(fname, pdf)

    with open(tmp.name, 'rb') as f:
        zip_bytes = f.read()
    os.unlink(tmp.name)
    zip_name = f"halltickets_{ex_date.isoformat()}_{sess}.zip"
    return Response(zip_bytes, mimetype='application/zip', headers={'Content-Disposition': f'attachment; filename={zip_name}'})


# New: Bulk timetable/allocation upload (Excel/CSV)
@app.route('/api/upload/timetable', methods=['POST'])
def upload_timetable():
    # Check if admin is logged in
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    try:
        # Read file
        if filename.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
        else:
            return jsonify({'error': 'Unsupported file format'}), 400

        # Expected columns (case-insensitive): Reg_No, Name of the Student, Dept, year,
        # SUB_CODE (or "SUB CODE"), SUB_TITLE (or "SUB TITLE"), DATE, SESS
        # Normalize columns
        df.columns = [str(c).strip().lower() for c in df.columns]

        # Flexible resolver for alternative header names
        def resolve(cols, *candidates):
            for c in candidates:
                if c in cols:
                    return c
            return None

        reg_col = resolve(df.columns, 'reg_no', 'reg no', 'regno')
        name_col = resolve(df.columns, 'name of the student', 'student name', 'name')
        dept_col = resolve(df.columns, 'dept', 'department')
        year_col = resolve(df.columns, 'year', 'prog & year', 'prog & year.')
        sub_code_col = resolve(df.columns, 'sub_code', 'sub code', 'paper code', 'subject code')
        sub_title_col = resolve(df.columns, 'sub_title', 'sub title', 'paper title', 'subject title')
        date_col = resolve(df.columns, 'date', 'exam date')
        sess_col = resolve(df.columns, 'sess', 'session')

        missing = []
        for key, val in [('reg_no', reg_col), ('name of the student', name_col), ('dept', dept_col),
                          ('year', year_col), ('sub_code', sub_code_col), ('sub_title', sub_title_col),
                          ('date', date_col), ('sess', sess_col)]:
            if not val:
                missing.append(key)
        if missing:
            return jsonify({'error': f'Missing required columns: {", ".join(missing)}'}), 400

        # Build a consistent 16-column view for Students page and persist to JSON
        try:
            desired_cols = [
                'SNO','ENQ','Reg_No','Name of the Student','Prog & Year','CLASS CODE','year','Degree','Dept',
                'DEPT ORD','CLASS ORD','SUB ORD','SUB_CODE','SUB_TITLE','DATE','SESS'
            ]
            # Helper to fetch by flexible naming using resolve()
            col_map = {}
            col_map['SNO'] = resolve(df.columns, 'sno')
            col_map['ENQ'] = resolve(df.columns, 'enq')
            col_map['Reg_No'] = reg_col
            col_map['Name of the Student'] = name_col
            col_map['Prog & Year'] = resolve(df.columns, 'prog & year', 'prog & year.')
            col_map['CLASS CODE'] = resolve(df.columns, 'class code', 'class_code', 'class')
            col_map['year'] = year_col
            col_map['Degree'] = resolve(df.columns, 'degree')
            col_map['Dept'] = dept_col
            col_map['DEPT ORD'] = resolve(df.columns, 'dept ord', 'dept_ord')
            col_map['CLASS ORD'] = resolve(df.columns, 'class ord', 'class_ord')
            col_map['SUB ORD'] = resolve(df.columns, 'sub ord', 'sub_ord')
            col_map['SUB_CODE'] = sub_code_col
            col_map['SUB_TITLE'] = sub_title_col
            col_map['DATE'] = date_col
            col_map['SESS'] = sess_col

            data_dict = {}
            for dc in desired_cols:
                src = col_map.get(dc)
                if src:
                    data_dict[dc] = df[src].astype(str)
                else:
                    data_dict[dc] = ""
            display_df = pd.DataFrame(data_dict, columns=desired_cols).fillna("")

            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            json_path = os.path.join(app.config['UPLOAD_FOLDER'], 'last_students.json')
            display_df.to_json(json_path, orient='records', force_ascii=False)
            session['last_students_json'] = json_path
        except Exception:
            # Non-fatal; continue normal timetable processing
            pass

        # Fetch halls and staff for allocation
        halls = Hall.query.order_by(Hall.capacity.desc()).all()
        if not halls:
            return jsonify({'error': 'No halls available to allocate'}), 400

        # Ensure a system staff exists to be assigned if none provided
        system_staff = Staff.query.filter_by(email='system@ems.local').first()
        if not system_staff:
            system_staff = Staff(name='System Allocator', email='system@ems.local', phone='0000000000', department='ADMIN', role='System')
            db.session.add(system_staff)
            db.session.flush()

        from datetime import datetime
        # Simple mapping for session to time
        session_to_time = {
            'FN': '09:30',
            'AN': '13:30',
            'EV': '16:00',
        }

        total_created_students = 0
        total_created_exams = 0
        total_created_attendance = 0
        allocation_summary = []

        # Group by exam slot (dept, year, sub_code, date, sess)
        group_cols = [dept_col, year_col, sub_code_col, date_col, sess_col, sub_title_col]
        for (dept, year, sub_code, date_str, sess, sub_title), group in df.groupby(group_cols):
            # Parse date and time
            try:
                if isinstance(date_str, str):
                    exam_date = datetime.strptime(date_str.strip(), '%d-%m-%Y').date()
                else:
                    # Excel date as datetime or Timestamp
                    exam_date = pd.to_datetime(date_str).date()
            except Exception:
                try:
                    exam_date = datetime.strptime(str(date_str), '%Y-%m-%d').date()
                except Exception:
                    return jsonify({'error': f'Invalid date format for {date_str}. Expected DD-MM-YYYY or YYYY-MM-DD'}), 400

            sess_key = str(sess).strip().upper()
            time_str = session_to_time.get(sess_key, '09:30')
            exam_time = datetime.strptime(time_str, '%H:%M').time()

            # Create an Exam per hall allocation chunk; we will split the group by hall capacities
            # Requirement: allocate in ascending order by Reg_No
            students_in_slot = []
            group_sorted = group.sort_values(by=[reg_col], kind='mergesort')
            for _, r in group_sorted.iterrows():
                reg_no = str(r[reg_col]).strip()
                student_name = str(r[name_col]).strip()
                # Find or create student (using reg_no as email surrogate)
                pseudo_email = f"{reg_no}@example.edu"
                student = Student.query.filter_by(email=pseudo_email).first()
                if not student:
                    student = Student(name=student_name, email=pseudo_email, phone='0000000000', department=str(dept), year=str(year))
                    db.session.add(student)
                    total_created_students += 1
                    db.session.flush()
                students_in_slot.append(student)

            # Allocate students to halls by capacity
            remaining = list(students_in_slot)
            hall_allocations = []  # list of (hall, [students])
            hall_idx = 0
            while remaining:
                if hall_idx >= len(halls):
                    return jsonify({'error': 'Not enough hall capacity to allocate all students for one or more slots'}), 400
                hall = halls[hall_idx]
                take = min(len(remaining), hall.capacity)
                allocated = remaining[:take]
                remaining = remaining[take:]
                hall_allocations.append((hall, allocated))
                hall_idx += 1

            # For each hall allocation, create an Exam and Attendance rows
            per_slot_summary = {'dept': str(dept), 'year': str(year), 'sub_code': str(sub_code), 'sub_title': str(sub_title), 'date': exam_date.isoformat(), 'session': sess_key, 'halls': []}

            for hall, allocated_students in hall_allocations:
                exam = Exam(subject=f"{sub_code} - {sub_title}", date=exam_date, time=exam_time, duration=180, hall_id=hall.id, staff_id=system_staff.id, department=str(dept), year=str(year), status='upcoming')
                db.session.add(exam)
                db.session.flush()
                total_created_exams += 1

                # Attendance create
                created_for_hall = 0
                for s in allocated_students:
                    att = Attendance(student_id=s.id, exam_id=exam.id, status='Absent', remarks='')
                    db.session.add(att)
                    created_for_hall += 1
                total_created_attendance += created_for_hall

                per_slot_summary['halls'].append({'hall_id': hall.id, 'hall_name': hall.name, 'allocated': created_for_hall})

            allocation_summary.append(per_slot_summary)

        db.session.commit()

        os.remove(file_path)

        return jsonify({
            'message': 'Timetable processed successfully',
            'created_students': total_created_students,
            'created_exams': total_created_exams,
            'created_attendance': total_created_attendance,
            'allocation': allocation_summary
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error processing timetable: {str(e)}'}), 500
    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass


# Export allotment/hall ticket CSV for a date + session
@app.route('/api/export/halltickets', methods=['GET'])
def export_hall_tickets():
    # Check if admin is logged in
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    date_str = request.args.get('date')
    sess = request.args.get('session', 'FN').upper()
    if not date_str:
        return jsonify({'error': 'Missing required query param: date (YYYY-MM-DD)'}), 400

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    # Get exams on date and approximate time by session mapping
    session_to_time = {
        'FN': '09:30',
        'AN': '13:30',
        'EV': '16:00',
    }
    time_str = session_to_time.get(sess)
    if not time_str:
        return jsonify({'error': 'Invalid session. Use FN, AN, or EV'}), 400

    # Fetch exams on that date matching time (exact HH:MM) if created by uploader
    target_time = datetime.strptime(time_str, '%H:%M').time()
    exams = Exam.query.filter(Exam.date == target_date, Exam.time == target_time).all()
    if not exams:
        return jsonify({'error': 'No exams found for given date/session'}), 404

    # Build CSV
    output = StringIO()
    # Header
    output.write('reg_no,student_name,department,year,subject,date,time,hall,seat_no\n')

    for exam in exams:
        # Attendance records are the allocation list
        atts = Attendance.query.filter_by(exam_id=exam.id).order_by(Attendance.id.asc()).all()
        # Seat numbers 1..N per hall (order by created id)
        seat_no = 1
        for att in atts:
            student = att.student
            # Derive reg_no from pseudo email pattern REGNO@example.edu if present
            reg_no = ''
            try:
                if student and student.email and '@' in student.email:
                    reg_no = student.email.split('@')[0]
            except Exception:
                reg_no = ''
            output.write(','.join([
                reg_no,
                (student.name if student else '' ).replace(',', ' '),
                (student.department if student else '').replace(',', ' '),
                (student.year if student else '').replace(',', ' '),
                (exam.subject or '').replace(',', ' '),
                exam.date.isoformat() if exam.date else '',
                exam.time.strftime('%H:%M') if exam.time else '',
                (exam.hall.name if exam.hall else '').replace(',', ' '),
                str(seat_no)
            ]) + '\n')
            seat_no += 1

    csv_data = output.getvalue()
    output.close()

    filename = f"halltickets_{date_str}_{sess}.csv"
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


# Render hall ticket for a single student by date/session
@app.route('/hall_ticket/<int:student_id>')
def hall_ticket(student_id: int):
    # Check if admin is logged in
    if 'admin_id' not in session:
        return redirect(url_for('login'))

    date_str = request.args.get('date')
    sess = (request.args.get('session') or 'FN').upper()
    if not date_str:
        from datetime import date as _date
        date_str = _date.today().isoformat()

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception:
        return render_template('hall_ticket_error.html', message='Invalid date format. Use YYYY-MM-DD')

    session_to_time = {'FN': '09:30', 'AN': '13:30', 'EV': '16:00'}
    time_str = session_to_time.get(sess)
    if not time_str:
        return render_template('hall_ticket_error.html', message='Invalid session. Use FN, AN, or EV')
    target_time = datetime.strptime(time_str, '%H:%M').time()

    student = Student.query.get_or_404(student_id)

    # Exams for the student are from Attendance linking the Exam
    atts = (
        Attendance.query
        .join(Exam, Attendance.exam_id == Exam.id)
        .filter(Attendance.student_id == student_id, Exam.date == target_date, Exam.time == target_time)
        .order_by(Exam.time.asc(), Attendance.id.asc())
        .all()
    )

    rows = []
    for idx, att in enumerate(atts, start=1):
        ex = att.exam
        rows.append({
            'date': ex.date.strftime('%d-%m-%Y') if ex.date else '',
            'session': sess,
            'paper_code': (ex.subject or '').split(' - ')[0],
            'paper_title': ' - '.join((ex.subject or '').split(' - ')[1:]) if ' - ' in (ex.subject or '') else (ex.subject or ''),
            'hall_no': ex.hall.name if ex and ex.hall else '',
            'seat_no': idx
        })

    college = {
        'name': 'KPR College of Arts Science and Research',
        'subtitle': 'CIA - I EXAMINATIONS - AUGUST 2025',
        'address': 'Avinashi Road, Arasur, Coimbatore-641 407.'
    }

    return render_template(
        'hall_ticket_single.html',
        student=student,
        programme_year=student.year,
        register_no=(student.email.split('@')[0] if student.email else ''),
        rows=rows,
        college=college,
        date_str=date_str,
        session=sess
    )

@app.route('/api/upload/halls', methods=['POST'])
def upload_halls():
    # Check if admin is logged in
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            # Determine file type and read accordingly
            if filename.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            else:
                return jsonify({'error': 'Unsupported file format'}), 400
            
            # Process the data and save to database
            saved_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # Check if hall already exists
                    existing_hall = Hall.query.filter_by(name=row['name']).first()
                    if existing_hall:
                        # Update existing hall
                        existing_hall.capacity = row['capacity']
                        existing_hall.location = row['location']
                        existing_hall.facilities = row.get('facilities', '')
                    else:
                        # Create new hall
                        hall = Hall(
                            name=row['name'],
                            capacity=row['capacity'],
                            location=row['location'],
                            facilities=row.get('facilities', '')
                        )
                        db.session.add(hall)
                    
                    saved_count += 1
                except Exception as e:
                    errors.append(f"Row {index + 1}: {str(e)}")
            
            db.session.commit()
            
            # Clean up uploaded file
            os.remove(file_path)
            
            return jsonify({
                'message': f'Successfully processed {saved_count} halls',
                'errors': errors
            }), 200
            
        except Exception as e:
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    
    return jsonify({'error': 'File upload failed'}), 500



# Dashboard data
@app.route('/api/dashboard')
def dashboard_data():
    total_students = Student.query.count()
    total_staff = Staff.query.count()
    total_halls = Hall.query.count()
    total_exams = Exam.query.count()
    
    # Recent exams
    recent_exams = Exam.query.order_by(Exam.date.desc()).limit(5).all()
    
    return jsonify({
        'total_students': total_students,
        'total_staff': total_staff,
        'total_halls': total_halls,
        'total_exams': total_exams,
        'recent_exams': [exam.to_dict() for exam in recent_exams]
    })



@app.route('/allotted_students')
def allotted_students():
    # Check if admin is logged in
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    return render_template('allotted_students.html')



# API to save hall allotment
@app.route('/api/save_allotment', methods=['POST'])
def save_allotment():
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'exam_id' not in data or not data['exam_id']:
            return jsonify({'error': 'Missing exam ID'}), 400
        
        exam = Exam.query.get(data['exam_id'])
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404
        
        # Update exam status to ongoing
        exam.status = 'ongoing'
        
        # If you have specific allotment data to save, add it here
        # For example, if you're saving which students are in which hall
        
        db.session.commit()
        return jsonify({'message': 'Hall allotment saved successfully', 'exam': exam.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to save allotment: {str(e)}'}), 500

# API to get allotted students history
@app.route('/api/allotted_students', methods=['GET'])
def get_allotted_students():
    try:
        # Get exams with ongoing status (allotted exams)
        allotted_exams = Exam.query.filter_by(status='ongoing').all()
        
        result = []
        for exam in allotted_exams:
            # Get attendance records for this exam
            attendances = Attendance.query.filter_by(exam_id=exam.id).all()
            
            exam_data = exam.to_dict()
            exam_data['attendances'] = [attendance.to_dict() for attendance in attendances]
            result.append(exam_data)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Failed to fetch allotted students: {str(e)}'}), 500

# API to mark exam as completed
@app.route('/api/exams/<int:id>/complete', methods=['POST'])
def complete_exam(id):
    try:
        exam = Exam.query.get_or_404(id)
        exam.status = 'completed'
        db.session.commit()
        return jsonify({'message': 'Exam marked as completed', 'exam': exam.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to complete exam: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health probe to check datastore connectivity."""
    info = {
        'use_mongo': USE_MONGO,
        'students_source': 'mongo' if USE_MONGO else 'sqlalchemy',
    }

    # Check Mongo connectivity (only if enabled)
    mongo_connected = False
    if USE_MONGO and mongo_db is not None:
        try:
            mongo_db.command('ping')
            mongo_connected = True
        except Exception:
            mongo_connected = False
    info['mongo_connected'] = mongo_connected

    # Check SQL connectivity via a lightweight query
    sql_connected = False
    try:
        _ = Admin.query.first()
        sql_connected = True
    except Exception:
        sql_connected = False
    info['sql_connected'] = sql_connected

    return jsonify(info), 200

if __name__ == '__main__':
    app.run(debug=True)