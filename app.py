import sqlite3
import csv
import io
import re
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import datetime # Import datetime for current date

# --- App Setup ---
app = Flask(__name__)
app.secret_key = 'your_super_secret_key_12345'
app.config['PHONE_REGEX'] = re.compile(r'^09\d{8}$') # Syrian phone format

# --- Database Functions ---
def get_db_connection():
    conn = sqlite3.connect('students.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
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
                notes TEXT, -- New: Optional notes field
                registration_date TEXT NOT NULL -- New: Registration date
            )
        ''')
        # Add indexes for faster search
        conn.execute('CREATE INDEX idx_student_name ON students(student_name)')
        conn.execute('CREATE INDEX idx_parent_name ON students(parent_name)') # Changed from idx_parent_phone
    print("Database initialized with schema constraints and indexes")

@app.cli.command('init-db')
def init_db_command():
    init_db()
    print("Database initialized successfully")

# --- Validation Utilities ---
def validate_phone(phone):
    return bool(app.config['PHONE_REGEX'].match(phone)) if phone else True

def validate_student_data(form_data, is_csv=False):
    errors = []
    required_fields = ['student_name', 'age', 'parent_name',
                       'parent_phone_1', 'grade', 'school_name',
                       'address', 'memorizing']

    # Check required fields
    for field in required_fields:
        if not form_data.get(field):
            errors.append(f"حقل '{field}' مطلوب")

    # Validate phone formats
    phones = [
        ('parent_phone_1', form_data.get('parent_phone_1')),
        ('parent_phone_2', form_data.get('parent_phone_2')),
        ('student_phone', form_data.get('student_phone'))
    ]

    for field, value in phones:
        if value and not validate_phone(value):
            errors.append(f"رقم الهاتف '{field}' غير صالح. يجب أن يكون 10 أرقام ويبدأ بـ 09")

    # Validate age
    try:
        age = int(form_data.get('age', 0))
        if not (5 <= age <= 25):
            errors.append("العمر يجب أن يكون بين 5 و 25 سنة")
    except ValueError:
        errors.append("العمر يجب أن يكون رقماً صحيحاً")

    # Validate registration_date format if provided
    reg_date_str = form_data.get('registration_date')
    if reg_date_str:
        try:
            # Attempt to parse the date. Format 'YYYY-MM-DD' is common for HTML date input
            datetime.datetime.strptime(reg_date_str, '%Y-%m-%d')
        except ValueError:
            errors.append("تاريخ التسجيل غير صالح. يجب أن يكون بالصيغة YYYY-MM-DD")

    return errors

# --- App Routes ---
@app.route('/')
def index():
    try:
        with get_db_connection() as conn:
            students = conn.execute('''
                SELECT * FROM students
                ORDER BY student_name ASC
            ''').fetchall()
        return render_template('index.html', students=students)
    except sqlite3.Error as e:
        flash(f'خطأ في قاعدة البيانات: {str(e)}', 'danger')
        return render_template('index.html', students=[])

@app.route('/add_student', methods=['POST'])
def add_student():
    form_data = request.form
    validation_errors = validate_student_data(form_data)

    if validation_errors:
        for error in validation_errors:
            flash(error, 'danger')
        return redirect(url_for('index'))

    # Get current date if registration_date is not provided
    registration_date = form_data.get('registration_date')
    if not registration_date:
        registration_date = datetime.date.today().isoformat() # YYYY-MM-DD format

    try:
        student_data = (
            form_data['student_name'],
            int(form_data['age']),
            form_data['parent_name'],
            form_data['parent_phone_1'],
            form_data.get('parent_phone_2') or None,
            form_data.get('student_phone') or None,
            form_data['grade'],
            form_data['school_name'],
            form_data['address'],
            form_data['memorizing'],
            form_data.get('notes') or None, # New: notes
            registration_date # New: registration_date
        )

        with get_db_connection() as conn:
            conn.execute('''
                INSERT INTO students (
                    student_name, age, parent_name,
                    parent_phone_1, parent_phone_2,
                    student_phone, grade, school_name,
                    address, memorizing, notes, registration_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', student_data)
            conn.commit()

        flash('تمت إضافة الطالب بنجاح!', 'success')
        return redirect(url_for('index'))

    except sqlite3.IntegrityError as e:
        flash(f'خطأ في قاعدة البيانات: {str(e)}', 'danger')
    except Exception as e:
        flash(f'خطأ غير متوقع: {str(e)}', 'danger')

    return redirect(url_for('index'))

@app.route('/modify_student/<int:student_id>', methods=['GET', 'POST'])
def modify_student(student_id):
    if request.method == 'GET':
        # Display the modification form
        try:
            with get_db_connection() as conn:
                student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()

            if student is None:
                flash('الطالب غير موجود.', 'danger')
                return redirect(url_for('index'))

            return render_template('modify_info.html', student=student)
        except sqlite3.Error as e:
            flash(f'خطأ في قاعدة البيانات: {str(e)}', 'danger')
            return redirect(url_for('index'))

    elif request.method == 'POST':
        # Process the modification form submission
        form_data = request.form
        validation_errors = validate_student_data(form_data)

        if validation_errors:
            for error in validation_errors:
                flash(error, 'danger')
            # Fetch student again to re-render form with current data and errors
            try:
                with get_db_connection() as conn:
                    student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
                return render_template('modify_info.html', student=student)
            except sqlite3.Error as e:
                flash(f'خطأ في قاعدة البيانات: {str(e)}', 'danger')
                return redirect(url_for('index'))

        # Get current date if registration_date is not provided during modification
        registration_date = form_data.get('registration_date')
        if not registration_date:
            registration_date = datetime.date.today().isoformat() # YYYY-MM-DD format


        try:
            student_data = (
                form_data['student_name'],
                int(form_data['age']),
                form_data['parent_name'],
                form_data['parent_phone_1'],
                form_data.get('parent_phone_2') or None,
                form_data.get('student_phone') or None,
                form_data['grade'],
                form_data['school_name'],
                form_data['address'],
                form_data['memorizing'],
                form_data.get('notes') or None, # New: notes
                registration_date, # New: registration_date
                student_id # The ID is the last parameter for the WHERE clause
            )

            with get_db_connection() as conn:
                conn.execute('''
                    UPDATE students SET
                        student_name = ?,
                        age = ?,
                        parent_name = ?,
                        parent_phone_1 = ?,
                        parent_phone_2 = ?,
                        student_phone = ?,
                        grade = ?,
                        school_name = ?,
                        address = ?,
                        memorizing = ?,
                        notes = ?,          -- New
                        registration_date = ? -- New
                    WHERE id = ?
                ''', student_data)
                conn.commit()

            flash('تم تحديث بيانات الطالب بنجاح!', 'success')
            return redirect(url_for('index'))

        except sqlite3.IntegrityError as e:
            flash(f'خطأ في قاعدة البيانات: {str(e)}', 'danger')
        except Exception as e:
            flash(f'خطأ غير متوقع: {str(e)}', 'danger')

        return redirect(url_for('index'))


@app.route('/import_csv', methods=['POST'])
def import_csv():
    if 'file' not in request.files:
        flash('لم يتم تقديم ملف', 'danger')
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash('لم يتم اختيار ملف', 'warning')
        return redirect(url_for('index'))

    if not file.filename.lower().endswith('.csv'):
        flash('صيغة الملف غير مدعومة. يجب أن يكون CSV', 'danger')
        return redirect(url_for('index'))

    try:
        stream = io.TextIOWrapper(file.stream, encoding='utf-8-sig')
        csv_reader = csv.reader(stream)
        valid_rows = []
        row_errors = []

        # Assuming CSV now has 12 columns: existing 10 + notes + registration_date
        expected_columns = 12

        for i, row in enumerate(csv_reader, 1):
            if len(row) != expected_columns:
                row_errors.append(f'السطر {i}: عدد الأعمدة غير صحيح ({expected_columns} مطلوبة)')
                continue

            # Map CSV columns to form fields
            student_data = {
                'student_name': row[0].strip(),
                'age': row[1].strip(),
                'parent_name': row[2].strip(),
                'parent_phone_1': row[3].strip(),
                'parent_phone_2': row[4].strip(),
                'student_phone': row[5].strip(),
                'grade': row[6].strip(),
                'school_name': row[7].strip(),
                'address': row[8].strip(),
                'memorizing': row[9].strip(),
                'notes': row[10].strip(),             # New: notes
                'registration_date': row[11].strip()  # New: registration_date
            }

            # If registration_date is empty in CSV, set to current date
            if not student_data['registration_date']:
                student_data['registration_date'] = datetime.date.today().isoformat()

            # Validate row
            errors = validate_student_data(student_data, is_csv=True)
            if errors:
                row_errors.append(f'السطر {i}: {"; ".join(errors)}')
                continue

            # Prepare for insertion
            valid_rows.append((
                student_data['student_name'],
                int(student_data['age']),
                student_data['parent_name'],
                student_data['parent_phone_1'],
                student_data['parent_phone_2'] or None,
                student_data['student_phone'] or None,
                student_data['grade'],
                student_data['school_name'],
                student_data['address'],
                student_data['memorizing'],
                student_data['notes'] or None,             # New: notes
                student_data['registration_date']          # New: registration_date
            ))

        # Process validation results
        if row_errors:
            flash(f'تم العثور على أخطاء في {len(row_errors)} سطراً', 'warning')
            for error in row_errors[:5]: # Show first 5 errors
                flash(error, 'danger')
            if len(row_errors) > 5:
                flash(f'...و {len(row_errors)-5} أخطاء إضافية', 'danger')

        if valid_rows:
            with get_db_connection() as conn:
                conn.executemany('''
                    INSERT INTO students (
                        student_name, age, parent_name,
                        parent_phone_1, parent_phone_2,
                        student_phone, grade, school_name,
                        address, memorizing, notes, registration_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', valid_rows)
                conn.commit()
            flash(f'تم استيراد {len(valid_rows)} طالب بنجاح', 'success')
        else:
            flash('لم يتم استيراد أي سجلات', 'warning')

    except csv.Error as e:
        flash(f'خطأ في معالجة CSV: {str(e)}', 'danger')
    except Exception as e:
        flash(f'خطأ غير متوقع: {str(e)}', 'danger')

    return redirect(url_for('index'))

# Route to download the CSV template
@app.route('/download_csv_template')
def download_csv_template():
    # The directory where the template.csv is located (your templates folder)
    # The second argument is the filename to be sent
    return send_from_directory(app.template_folder, 'template.csv', as_attachment=True)

# Route for the "تسجيل حضور أو حفظ" page
@app.route('/record')
def record():
    return render_template('record.html')

# Route for the "النقاط" page
@app.route('/points')
def points():
    return render_template('points.html')

@app.route('/delete_student/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    try:
        with get_db_connection() as conn:
            # First, check if the student exists
            student = conn.execute('SELECT id FROM students WHERE id = ?', (student_id,)).fetchone()
            if student is None:
                flash('الطالب غير موجود.', 'danger')
                return redirect(url_for('index'))

            conn.execute('DELETE FROM students WHERE id = ?', (student_id,))
            conn.commit()
            flash('تم حذف الطالب بنجاح!', 'success')
    except sqlite3.Error as e:
        flash(f'خطأ في قاعدة البيانات أثناء الحذف: {str(e)}', 'danger')
    except Exception as e:
        flash(f'خطأ غير متوقع أثناء الحذف: {str(e)}', 'danger')

    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)