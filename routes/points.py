import sqlite3
from flask import Blueprint, render_template, request, flash, redirect, url_for
from app import get_db_connection

points_bp = Blueprint('points', __name__)

@points_bp.route('/points', methods=['GET', 'POST'])
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
