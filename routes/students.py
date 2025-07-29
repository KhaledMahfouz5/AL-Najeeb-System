from flask import Blueprint, render_template, request, redirect, url_for, flash
import sqlite3
from app import get_db_connection, validate_student_data
import datetime
from typing import Any

students_bp = Blueprint('students', __name__)

@students_bp.route('/')
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

@students_bp.route('/add_student', methods=['POST'])
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

@students_bp.route('/modify_student/<int:student_id>', methods=['GET', 'POST'])
def modify_student(student_id: int) -> Any :
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
                return redirect(url_for('students.index'))

            return render_template('modify_info.html', student=student)
        except sqlite3.Error as e:
            flash(f'خطأ في قاعدة البيانات: {str(e)}', 'danger')
            return redirect(url_for('students.index'))

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
                return redirect(url_for('students.index'))

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
            return redirect(url_for('students.index'))

        except sqlite3.IntegrityError as e:
            flash(f'خطأ في قاعدة البيانات: {str(e)}', 'danger')
        except Exception as e:
            flash(f'خطأ غير متوقع: {str(e)}', 'danger')
        return redirect(url_for('students.index'))

@students_bp.route('/delete_student/<int:student_id>', methods=['POST'])
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
