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
        conn.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_name TEXT NOT NULL,
                phone_number TEXT NOT NULL
            )
        ''')
    print("Database initialized and 'students' table created.")

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
    students = conn.execute('SELECT * FROM students').fetchall()
    conn.close()
    # The 'students' variable is passed to the HTML template
    return render_template('index.html', students=students)

@app.route('/add', methods=['POST'])
def add_student():
    """Handles the form submission for adding a new student."""
    # Get data from the form submitted in index.html
    name = request.form['name']
    parent_name = request.form['parent_name']
    phone_number = request.form['phone_number']

    # Insert the new student record into the database
    conn = get_db_connection()
    conn.execute('INSERT INTO students (name, parent_name, phone_number) VALUES (?, ?, ?)',
                 (name, parent_name, phone_number))
    conn.commit()
    conn.close()

    # Redirect back to the main page to see the updated list
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Initialize the database when the script is run directly
    init_db()
    # Run the Flask development server
    app.run(debug=True)
