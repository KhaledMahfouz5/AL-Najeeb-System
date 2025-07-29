import sqlite3
import csv
import io
import re
import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
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
        flash(f'خطأ في معالشة CSV: {str(e)}', 'danger')
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
        # Now student_id will be a list of selected IDs from the checkboxes
        selected_student_ids = request.form.getlist('student_id')
        point_amount_str = request.form.get('point_amount')
        operation = request.form.get('operation')

        if not selected_student_ids or not point_amount_str or not operation:
            flash('الرجاء اختيار طالب واحد على الأقل وتعبئة جميع الحقول المطلوبة.', 'danger')
            return redirect(url_for('points'))

        try:
            point_amount = int(point_amount_str)

            if point_amount <= 0:
                flash('الرجاء إدخال قيمة نقاط أكبر من صفر.', 'danger')
                return redirect(url_for('points'))

            with get_db_connection() as conn:
                # Ensure IDs are integers and unique
                int_selected_ids = sorted(list(set([int(sid) for sid in selected_student_ids if sid.isdigit()])))
                if not int_selected_ids:
                    flash('لم يتم تحديد أي طالب صالح.', 'danger')
                    return redirect(url_for('points'))

                placeholders = ','.join(['?'] * len(int_selected_ids))
                query = f"SELECT id, student_name, points FROM students WHERE id IN ({placeholders})"
                students_to_update = conn.execute(query, int_selected_ids).fetchall()

                if not students_to_update:
                    flash('لم يتم العثور على أي طلاب مطابقين للاختيار.', 'danger')
                    return redirect(url_for('points'))

                updated_details = []
                for student in students_to_update:
                    current_points = student['points']
                    student_name = student['student_name']
                    new_points = current_points

                    if operation == 'add':
                        new_points += point_amount
                    elif operation == 'remove':
                        if current_points < point_amount:
                            new_points = 0 # Cap at zero
                        else:
                            new_points -= point_amount
                    else:
                        flash('عملية غير صالحة.', 'danger')
                        return redirect(url_for('points'))

                    conn.execute('UPDATE students SET points = ? WHERE id = ?', (new_points, student['id']))
                    updated_details.append(f"{student_name} (أصبح {new_points})")

                conn.commit()

                flash_op_text = "إضافة" if operation == "add" else "خصم"
                if len(updated_details) == 1:
                    flash(f'تمت عملية {flash_op_text} النقاط للطالب {updated_details[0].replace(" (أصبح", " والنقاط الجديدة")}.', 'success')
                else:
                    flash_message_head = f'تمت عملية {flash_op_text} النقاط لـ {len(updated_details)} طلاب.'
                    flash_message_body = 'التفاصيل: ' + ', '.join(updated_details[:5])
                    if len(updated_details) > 5:
                        flash_message_body += f'... والمزيد.'
                    flash(f'{flash_message_head} {flash_message_body}', 'success')

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