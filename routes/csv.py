from flask import Blueprint, send_from_directory, flash, redirect, url_for, request
import csv
import io
import io
import csv
import datetime
from app import validate_student_data , get_db_connection

csv_bp = Blueprint('csv', __name__)

@csv_bp.route('/import_csv', methods=['POST'])
def import_csv():
    if 'file' not in request.files:
        flash('لم يتم تقديم ملف', 'danger')
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash('لم يتم اختيار ملف', 'warning')
        return redirect(url_for('index'))

    if not str(file.filename).lower().endswith('.csv'):
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

            errors = validate_student_data(student_data)
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

@csv_bp.route('/download_csv_template')
def download_csv_template():
    return send_from_directory('templates', 'template.csv', as_attachment=True)
