import sqlite3
from flask import Flask, render_template, request, redirect, url_for

# Create a Flask application instance
app = Flask(__name__)

# --- Database Functions ---

def get_db_connection():
    """Creates and returns a connection to the SQLite database."""
    conn = sqlite3.connect('students.db')
    # Return rows as dictionaries, so we can access columns by name
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates the 'students' table if it doesn't exist."""
    conn = get_db_connection()
    # Use a 'with' statement to automatically handle closing the connection
    with conn:
        # Drop the table if it exists to ensure the new schema is applied
        conn.execute('DROP TABLE IF EXISTS students')
        # Create the table with the new, expanded schema
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

# Command to initialize the database from the command line: flask init-db
@app.cli.command('init-db')
def init_db_command():
    """Clear existing data and create new tables."""
    init_db()


# --- App Routes ---

@app.route('/')
def index():
    """Renders the main page with the list of students."""
    conn = get_db_connection()
    # Select all columns to display in the table
    students = conn.execute('SELECT * FROM students ORDER BY id').fetchall()
    conn.close()
    # The 'students' variable is passed to the HTML template
    return render_template('index.html', students=students)

@app.route('/add', methods=['POST'])
def add_student():
    """Handles the form submission for adding a new student."""
    # Get all the new data from the form submitted in index.html
    student_name = request.form['student_name']
    age = request.form['age']
    parent_name = request.form['parent_name']
    parent_phone_1 = request.form['parent_phone_1']
    parent_phone_2 = request.form.get('parent_phone_2') # .get() for optional fields
    student_phone = request.form.get('student_phone')   # .get() for optional fields
    grade = request.form['grade']
    school_name = request.form['school_name']
    address = request.form['address']
    memorizing = request.form['memorizing']


    # Insert the new student record into the database with all fields
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO students (student_name, age, parent_name, parent_phone_1, parent_phone_2, student_phone, grade, school_name, address, memorizing)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (student_name, age, parent_name, parent_phone_1, parent_phone_2, student_phone, grade, school_name, address, memorizing))
    conn.commit()
    conn.close()

    # Redirect back to the main page to see the updated list
    return redirect(url_for('index'))

if __name__ == '__main__':
    # You can remove the init_db() call from here if you are using the flask command
    # It's good practice to manage the DB initialization separately.
    app.run(debug=True)
