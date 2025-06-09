import sqlite3
import csv
import io
# The 'flash' import is no longer needed
from flask import Flask, render_template, request, redirect, url_for

# Create a Flask application instance
app = Flask(__name__)
# The 'secret_key' is no longer required as we are not using flash/sessions
# app.secret_key = 'your_super_secret_key_12345'


# --- Database Functions ---

def get_db_connection():
    """Creates and returns a connection to the SQLite database."""
    conn = sqlite3.connect('students.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database. THIS IS ONLY RUN MANUALLY from the command line."""
    conn = get_db_connection()
    with conn:
        conn.execute('DROP TABLE IF EXISTS students')
        conn.execute('''
            CREATE TABLE students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                age INTEGER NOT NULL,
                parent_name TEXT NOT NULL,
                parent_phone_1 TEXT NOT NULL,
                parent_phone_2 TEXT,
                student_phone TEXT,
                grade TEXT NOT NULL,
                school_name TEXT NOT NULL,
                address TEXT NOT NULL,
                memorizing TEXT NOT NULL
            )
        ''')
    print("Database initialized and 'students' table created with the new schema.")

@app.cli.command('init-db')
def init_db_command():
    """Clears existing data and creates new tables."""
    init_db()


# --- App Routes ---

@app.route('/')
def index():
    """Renders the main page and displays any messages passed in the URL."""
    # Get the message from the URL query parameters
    message = request.args.get('message', None)
    category = request.args.get('category', None)
    
    conn = get_db_connection()
    students = conn.execute('SELECT * FROM students ORDER BY id').fetchall()
    conn.close()
    
    # Pass the message and students to the template
    return render_template('index.html', students=students, message=message, category=category)

@app.route('/add', methods=['POST'])
def add_student():
    """Handles the form submission for adding a single new student."""
    try:
        student_name = request.form['student_name']
        age = request.form['age']
        parent_name = request.form['parent_name']
        parent_phone_1 = request.form['parent_phone_1']
        parent_phone_2 = request.form.get('parent_phone_2')
        student_phone = request.form.get('student_phone')
        grade = request.form['grade']
        school_name = request.form['school_name']
        address = request.form['address']
        memorizing = request.form['memorizing']
        
        if not all([student_name, age, parent_name, parent_phone_1, grade, school_name, address, memorizing]):
             # Instead of flashing, redirect with a message
             return redirect(url_for('index', message='الرجاء تعبئة جميع الحقول المطلوبة.', category='danger'))

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO students (student_name, age, parent_name, parent_phone_1, parent_phone_2, student_phone, grade, school_name, address, memorizing)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (student_name, age, parent_name, parent_phone_1, parent_phone_2, student_phone, grade, school_name, address, memorizing))
        conn.commit()
        conn.close()
        
        message = 'تمت إضافة الطالب الجديد بنجاح!'
        category = 'success'
    except Exception as e:
        message = f'حدث خطأ أثناء إضافة الطالب: {e}'
        category = 'danger'

    return redirect(url_for('index', message=message, category=category))

@app.route('/import', methods=['POST'])
def import_csv():
    """Handles CSV import and redirects with a status message in the URL."""
    if 'file' not in request.files or request.files['file'].filename == '':
        return redirect(url_for('index', message='لم يتم اختيار أي ملف.', category='danger'))

    file = request.files['file']

    if file and file.filename.endswith('.csv'):
        students_to_add = [] # This is our "2D vector"
        try:
            stream = io.StringIO(file.stream.read().decode("utf-8-sig"), newline=None)
            csv_reader = csv.reader(stream)
            
            # First, read all rows from CSV into the students_to_add list
            for i, row in enumerate(csv_reader, start=1):
                if len(row) != 10:
                    msg = f'خطأ في ملف CSV في السطر رقم {i}: يجب أن يحتوي السطر على 10 أعمدة.'
                    return redirect(url_for('index', message=msg, category='danger'))
                try:
                    # Validate and prepare the row data
                    student_data = (
                        row[0], int(row[1]), row[2], row[3],
                        row[4] if row[4] else None, row[5] if row[5] else None,
                        row[6], row[7], row[8], row[9]
                    )
                    students_to_add.append(student_data)
                except ValueError:
                    msg = f"خطأ في ملف CSV في السطر رقم {i}: يجب أن يكون العمر (العمود الثاني) رقماً."
                    return redirect(url_for('index', message=msg, category='danger'))

            # If the list was successfully built, proceed to add to the database
            if students_to_add:
                conn = get_db_connection()
                # Use a try/except block for the database operation
                try:
                    # Now, loop through the "2D vector" and add each student one by one
                    for student in students_to_add:
                        conn.execute('''
                            INSERT INTO students (student_name, age, parent_name, parent_phone_1, parent_phone_2, student_phone, grade, school_name, address, memorizing)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', student)
                    
                    # If all insertions succeed, commit them to the database
                    conn.commit()
                    message = f'تم استيراد وإضافة {len(students_to_add)} طالب بنجاح!'
                    category = 'success'
                except sqlite3.Error as e:
                    # If any error occurs during insertion, the transaction is rolled back automatically
                    message = f'حدث خطأ في قاعدة البيانات أثناء الإضافة: {e}'
                    category = 'danger'
                finally:
                    # Always close the connection
                    conn.close()
            else:
                message = 'ملف CSV فارغ أو لا يمكن معالجته.'
                category = 'warning'

        except Exception as e:
            message = f'حدث خطأ غير متوقع أثناء عملية الاستيراد: {e}'
            category = 'danger'
        
        return redirect(url_for('index', message=message, category=category))
    else:
        return redirect(url_for('index', message='صيغة الملف غير صالحة. الرجاء رفع ملف .csv فقط.', category='danger'))


if __name__ == '__main__':
    app.run(debug=True)
