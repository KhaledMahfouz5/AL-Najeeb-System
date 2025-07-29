import sqlite3
import re
import os
from flask import Flask, render_template
import datetime

# --- App Setup ---
app = Flask(__name__)
app.secret_key = 'your_super_secret_key_12345'
app.config['PHONE_REGEX'] = re.compile(r'^09\d{8}$') # Syrian phone format

# Define the path to the database folder
DATABASE_FOLDER = os.path.join(app.root_path, 'databases')
DATABASE_FILE = os.path.join(DATABASE_FOLDER, 'students.db')

# --- Database Functions ---
def get_db_connection():
    os.makedirs(DATABASE_FOLDER, exist_ok=True)
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(DATABASE_FOLDER, exist_ok=True)
    with get_db_connection() as conn:
        conn.execute('DROP TABLE IF EXISTS students')
        conn.execute('''
            CREATE TABLE students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                age INTEGER NOT NULL CHECK(age BETWEEN 5 AND 25),
                parent_name TEXT NOT NULL,
                parent_phone_1 TEXT NOT NULL CHECK(length(parent_phone_1) = 10),
                parent_phone_2 TEXT CHECK(length(parent_phone_2) = 10 OR parent_phone_2 IS NULL),
                student_phone TEXT CHECK(length(student_phone) = 10 OR student_phone IS NULL),
                grade TEXT NOT NULL,
                school_name TEXT NOT NULL,
                address TEXT NOT NULL,
                memorizing TEXT NOT NULL,
                notes TEXT,
                registration_date TEXT NOT NULL,
                points INTEGER DEFAULT 0 NOT NULL
            )
        ''')
        conn.execute('CREATE INDEX idx_student_name ON students(student_name)')
        conn.execute('CREATE INDEX idx_parent_name ON students(parent_name)')
    print("Database initialized with schema constraints and indexes")

@app.cli.command('init-db')
def init_db_command():
    init_db()
    print("Database initialized successfully")

# --- Validation Utilities ---
def validate_phone(phone):
    return bool(app.config['PHONE_REGEX'].match(phone)) if phone else True

def validate_student_data(form_data):
    errors = []
    required_fields = ['student_name', 'age', 'parent_name',
                       'parent_phone_1', 'grade', 'school_name',
                       'address', 'memorizing']

    for field in required_fields:
        if not form_data.get(field):
            errors.append(f"حقل '{field}' مطلوب")

    phones = [
        ('parent_phone_1', form_data.get('parent_phone_1')),
        ('parent_phone_2', form_data.get('parent_phone_2')),
        ('student_phone', form_data.get('student_phone'))
    ]

    for field, value in phones:
        if value and not validate_phone(value):
            errors.append(f"رقم الهاتف '{field}' غير صالح. يجب أن يكون 10 أرقام ويبدأ بـ 09")

    try:
        age = int(form_data.get('age', 0))
        if not (5 <= age <= 25):
            errors.append("العمر يجب أن يكون بين 5 و 25 سنة")
    except ValueError:
        errors.append("العمر يجب أن يكون رقماً صحيحاً")

    reg_date_str = form_data.get('registration_date')
    if reg_date_str:
        try:
            datetime.datetime.strptime(reg_date_str, '%Y-%m-%d')
        except ValueError:
            errors.append("تاريخ التسجيل غير صالح. يجب أن يكون بالصيغة YYYY-MM-DD")

    return errors

# --- App Routes ---
@app.route('/record')
def record():
    return render_template('record.html')

if __name__ == '__main__':
    app.run(debug=True)
