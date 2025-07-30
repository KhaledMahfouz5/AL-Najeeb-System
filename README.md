# AL Najeeb System

---

## Introduction

AL Najeeb System is a simple web application built with the **Flask** framework in Python, utilizing **SQLite** as its database. This application allows users to manage student information, including personal data, contact details, memorization progress, and a points tracking system. The frontend is built with **Tailwind CSS** for a clean and responsive user experience.

---

## Installation and Running

Follow these streamlined steps to get the application up and running on your local machine.

### Prerequisites

* **Python 3.8** or newer
* `git` (for cloning the repository)

### Installation

1.  **Clone the repository:**
    Open your terminal and clone the project repository:
    ```bash
    git clone --depth 1 <your-repository-url>
    cd <your-project-directory>
    ```

2.  **Set up your Python Environment:**
    Create and activate a virtual environment, then install the required Python packages.
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Initialize your database IF needed**
    run `flask init-db` if the `databases/` directory is empty .
    > the `flask init-db` will delete the students.db if exists and creates a new empty one .

4.  **Start The App**
    Make sure the `serve.sh` script is executable:
    ```bash
    chmod +x serve.sh
    ```
    Then run it:
    ```bash
    ./serve.sh
    ```

5.  **Access the application:**
    After `serve.sh` successfully runs, open your web browser and navigate to:
    `http://127.0.0.1:8000/`

---

## How to Update

Updating the application involves pulling the latest code, updating dependencies, and carefully handling any database changes.

1.  **Stop the Current Application:**
    If the application is running, stop it by pressing `Ctrl + C` in the terminal window where Gunicorn is running.

2.  **Update the Code:**
    Ensure you are in your project directory and pull the latest changes from your Git repository:
    ```bash
    git pull
    ```

3.  **Activate the Virtual Environment:**
    Before installing dependencies or running database updates, always activate your virtual environment:
    ```bash
    source .venv/bin/activate # Linux/macOS
    .venv\Scripts\activate.bat # Windows Command Prompt
    .venv\Scripts\Activate.ps1 # Windows PowerShell
    ```

4.  **Update Dependencies:**
    If the project's dependencies have changed, update them.
    ```bash
    pip install -r requirements.txt 
    ```

5.  **Update the Database (Important):**
    **This is the most critical and sensitive step when updating an application that uses an SQLite database.**
    Since I still not using a dedicated database migration tool (like Flask-Migrate / Alembic), database schema updates must be handled manually.
    * The safest method without a migration tool is to:
            1.  **Backup your current data:** Copy your `databases/students.db` file to a safe, external location.
                ```bash
                cp databases/students.db databases/students_backup_$(date +%Y%m%d%H%M%S).db
                ```
            2.  **Reinitialize the database:**
                ```bash
                flask init-db
                ```
                **Note:** This will delete the old database and recreate a new, empty schema. You will then need to manually re-import your backed-up data if you wish to restore it (e.g., using a SQLite browser tool to import from CSVs you might have exported).

6.  **Restart the Application:**
    After updating the code and managing the database, restart the application:
    ```bash
    ./serve.sh
    ```
---
