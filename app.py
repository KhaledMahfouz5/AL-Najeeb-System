import sqlite3
import csv
import io
import re
import os # Import the os module
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import datetime

# --- App Setup ---
app = Flask(__name__)
app.secret_key = 'your_super_secret_key_12345'
app.config['PHONE_REGEX'] = re.compile(r'^09\d{8}$') # Syrian phone format

# Define the path to the database folder
# This creates a path like 'your_project/databases/students.db'
DATABASE_FOLDER = os.path.join(app.root_path, 'databases') # Use app.root_path for reliable directory
DATABASE_FILE = os.path.join(DATABASE_FOLDER, 'students.db')

# --- Database Functions ---
def get_db_connection():
    # Ensure the database folder exists before connecting
    os.makedirs(DATABASE_FOLDER, exist_ok=True)
    conn = sqlite3.connect(DATABASE_FILE) # Connect to the specified path
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # Ensure the database folder exists before creating the DB file
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
        # Add indexes for faster search
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

def validate_student_data(form_data, is_csv=False):
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
@app.route('/')
def index():
    try:
        with get_db_connection() as conn:
            students = conn.execute('''
                SELECT id, student_name, age, parent_name, parent_phone_1, parent_phone_2,
                       student_phone, grade, school_name, address, memorizing, notes,
                       registration_date, points
                FROM students
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

    registration_date = form_data.get('registration_date')
    if not registration_date:
        registration_date = datetime.date.today().isoformat()

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
            form_data.get('notes') or None,
            registration_date,
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
        try:
            with get_db_connection() as conn:
                student = conn.execute('''
                    SELECT id, student_name, age, parent_name, parent_phone_1, parent_phone_2,
                           student_phone, grade, school_name, address, memorizing, notes,
                           registration_date, points
                    FROM students WHERE id = ?''', (student_id,)).fetchone()

            if student is None:
                flash('الطالب غير موجود.', 'danger')
                return redirect(url_for('index'))

            return render_template('modify_info.html', student=student)
        except sqlite3.Error as e:
            flash(f'خطأ في قاعدة البيانات: {str(e)}', 'danger')
            return redirect(url_for('index'))

    elif request.method == 'POST':
        form_data = request.form
        validation_errors = validate_student_data(form_data)

        if validation_errors:
            for error in validation_errors:
                flash(error, 'danger')
            try:
                with get_db_connection() as conn:
                    student = conn.execute('''
                        SELECT id, student_name, age, parent_name, parent_phone_1, parent_phone_2,
                               student_phone, grade, school_name, address, memorizing, notes,
                               registration_date, points
                        FROM students WHERE id = ?''', (student_id,)).fetchone()
                return render_template('modify_info.html', student=student)
            except sqlite3.Error as e:
                flash(f'خطأ في قاعدة البيانات: {str(e)}', 'danger')
                return redirect(url_for('index'))

        registration_date = form_data.get('registration_date')
        if not registration_date:
            try:
                with get_db_connection() as conn:
                    original_student = conn.execute('SELECT registration_date FROM students WHERE id = ?', (student_id,)).fetchone()
                    if original_student:
                        registration_date = original_student['registration_date']
                    else:
                        registration_date = datetime.date.today().isoformat()
            except sqlite3.Error:
                registration_date = datetime.date.today().isoformat()

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
                form_data.get('notes') or None,
                registration_date,
                student_id
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
                        notes = ?,
                        registration_date = ?
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

        expected_columns = 12

        for i, row in enumerate(csv_reader, 1):
            if len(row) != expected_columns:
                row_errors.append(f'السطر {i}: عدد الأعمدة غير صحيح ({expected_columns} مطلوبة)')
                continue

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
                'notes': row[10].strip(),
                'registration_date': row[11].strip()
            }

            if not student_data['registration_date']:
                student_data['registration_date'] = datetime.date.today().isoformat()

            errors = validate_student_data(student_data, is_csv=True)
            if errors:
                row_errors.append(f'السطر {i}: {"; ".join(errors)}')
                continue

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
                student_data['notes'] or None,
                student_data['registration_date']
            ))

        if row_errors:
            flash(f'تم العثور على أخطاء في {len(row_errors)} سطراً', 'warning')
            for error in row_errors[:5]:
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

@app.route('/download_csv_template')
def download_csv_template():
    return send_from_directory(app.template_folder, 'template.csv', as_attachment=True)

@app.route('/record')
def record():
    return render_template('record.html')

@app.route('/points', methods=['GET', 'POST'])
def points():
    if request.method == 'POST':
        # Check for 'all_students' checkbox first
        apply_to_all_students = 'all_students' in request.form
        student_id = request.form.get('student_id') # This will be empty if 'all_students' is checked
        point_amount_str = request.form.get('point_amount')
        operation = request.form.get('operation') # 'add' or 'remove'

        if (not apply_to_all_students and not student_id) or not point_amount_str or not operation:
            flash('الرجاء اختيار طالب واحد على الأقل (أو كل الطلاب) وتعبئة جميع الحقول المطلوبة.', 'danger')
            return redirect(url_for('points'))

        try:
            point_amount = int(point_amount_str)

            if point_amount <= 0: # Changed from < 0 to <= 0
                flash('الرجاء إدخال قيمة نقاط أكبر من صفر.', 'danger')
                return redirect(url_for('points'))

            with get_db_connection() as conn:
                students_to_update = []
                if apply_to_all_students:
                    students_to_update = conn.execute('SELECT id, student_name, points FROM students').fetchall()
                else:
                    # Fetch single student if not applying to all
                    student = conn.execute('SELECT id, student_name, points FROM students WHERE id = ?', (student_id,)).fetchone()
                    if student:
                        students_to_update.append(student)
                    else:
                        flash('الطالب المحدد غير موجود.', 'danger')
                        return redirect(url_for('points'))

                if not students_to_update:
                    flash('لا يوجد طلاب لتحديث نقاطهم.', 'warning')
                    return redirect(url_for('points'))

                updated_count = 0
                for student in students_to_update:
                    current_points = student['points']
                    student_name = student['student_name']
                    new_points = current_points
                    applied_amount = point_amount # Amount actually applied for logging/messages

                    if operation == 'add':
                        new_points += point_amount
                        flash_message_prefix = f'تمت إضافة {point_amount} نقطة لـ {student_name}.'
                    elif operation == 'remove':
                        if current_points < point_amount:
                            applied_amount = current_points # Only remove what's available
                            new_points = 0 # Cap at zero
                            flash_message_prefix = (f'لا يمكن خصم {point_amount} نقطة من {student_name} حيث يمتلك {current_points} نقطة فقط. '
                                                    f'تم خصم {applied_amount} نقطة وتعيين النقاط إلى 0.')
                        else:
                            new_points -= point_amount
                            flash_message_prefix = f'تم خصم {point_amount} نقطة من {student_name}.'
                    else:
                        flash('عملية غير صالحة.', 'danger')
                        return redirect(url_for('points'))

                    conn.execute('UPDATE students SET points = ? WHERE id = ?', (new_points, student['id']))
                    updated_count += 1
                    # Flash message per student if not all, or accumulate for all
                    if not apply_to_all_students:
                        flash(f'{flash_message_prefix} النقاط الجديدة لـ {student_name}: {new_points}', 'success' if new_points >=0 else 'warning') # category based on points
                conn.commit()

                if apply_to_all_students:
                    total_students = len(students_to_update)
                    flash_op_text = "إضافة" if operation == "add" else "خصم"
                    flash(f'تم {flash_op_text} {point_amount} نقطة لـ {updated_count} طالب بنجاح.', 'success')


        except ValueError:
            flash('النقاط يجب أن تكون أرقاماً صحيحة.', 'danger')
        except sqlite3.Error as e:
            flash(f'خطأ في قاعدة البيانات: {str(e)}', 'danger')
        except Exception as e:
            flash(f'خطأ غير متوقع: {str(e)}', 'danger')

        return redirect(url_for('points'))

    else: # GET request
        try:
            with get_db_connection() as conn:
                students = conn.execute('SELECT id, student_name, points FROM students ORDER BY student_name ASC').fetchall()
            return render_template('points.html', students=students)
        except sqlite3.Error as e:
            flash(f'خطأ في قاعدة البيانات: {str(e)}', 'danger')
            return render_template('points.html', students=[])

@app.route('/delete_student/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    try:
        with get_db_connection() as conn:
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
