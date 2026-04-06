from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from config import Config
from functools import wraps
app = Flask(__name__)
app.config.from_object(Config)

def login_required(role=None):
    """Decorator to ensure user is logged in and optionally has a specific role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                flash('Unauthorized access', 'danger')
                return redirect(url_for('home')) # Redirect to appropriate dashboard or login
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Admin: Edit Faculty Assignments ---
@app.route('/admin/edit_faculty/<int:faculty_id>', methods=['GET', 'POST'])
@login_required('admin')
def edit_faculty(faculty_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT id, name, email FROM users WHERE id=%s AND role='faculty'", (faculty_id,))
        faculty = cur.fetchone()
        cur.execute("SELECT id, name FROM classes ORDER BY name")
        classes = cur.fetchall()
        cur.execute("SELECT id, name FROM divisions ORDER BY name")
        divisions = cur.fetchall()
        cur.execute("SELECT id, name, class_id FROM subjects ORDER BY name")
        subjects = cur.fetchall()
        cur.execute("SELECT * FROM faculty_assignments WHERE faculty_user_id=%s", (faculty_id,))
        assignments = cur.fetchall()
        # Build class->subjects mapping
        class_subjects = {c['id']: [s for s in subjects if s['class_id'] == c['id']] for c in classes}
        # Build class->divisions mapping
        cur.execute("SELECT class_id, division_id FROM class_divisions")
        class_div_rows = cur.fetchall()
        class_divisions = {c['id']: [] for c in classes}
        div_dict = {d['id']: d for d in divisions}
        for row in class_div_rows:
            if row['class_id'] in class_divisions and row['division_id'] in div_dict:
                class_divisions[row['class_id']].append(div_dict[row['division_id']])
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        # Check for duplicate email (excluding current faculty)
        with db.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email=%s AND id!=%s", (email, faculty_id))
            duplicate = cur.fetchone()
            if duplicate:
                flash('This email is already used by another user. Please use a different email.', 'danger')
                return redirect(url_for('edit_faculty', faculty_id=faculty_id))
            # Update faculty details
            cur.execute("UPDATE users SET name=%s, email=%s WHERE id=%s", (name, email, faculty_id))
            # Remove old assignments
            cur.execute("DELETE FROM faculty_assignments WHERE faculty_user_id=%s", (faculty_id,))
            # Add new assignments
            idx = 1
            while True:
                subject_id = request.form.get(f'subject_id_{idx}')
                class_id = request.form.get(f'class_id_{idx}')
                division_id = request.form.get(f'division_id_{idx}')
                if not subject_id or not class_id or not division_id:
                    break
                cur.execute("INSERT INTO faculty_assignments (faculty_user_id, subject_id, class_id, division_id) VALUES (%s, %s, %s, %s)", (faculty_id, subject_id, class_id, division_id))
                idx += 1
            db.commit()
        db.close()
        flash('Faculty details and assignments updated!', 'success')
        return redirect(url_for('admin_faculties'))
    db.close()
    return render_template('edit_faculty.html', faculty=faculty, assignments=assignments, classes=classes, divisions=divisions, subjects=subjects, class_subjects=class_subjects, class_divisions=class_divisions)
"""
--- Imports and App Initialization (must be at the top) ---
"""
''

def login_required(role=None):
    """Decorator to ensure user is logged in and optionally has a specific role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                flash('Unauthorized access', 'danger')
                return redirect(url_for('home')) # Redirect to appropriate dashboard or login
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Admin: Review & Publish Results ---
@app.route('/admin/review_results', methods=['GET', 'POST'])
@login_required('admin')
def admin_review_results():
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT e.*, c.name as class_name FROM exams e JOIN classes c ON e.class_id = c.id ORDER BY e.year DESC, e.month DESC, e.name")
        exams = cur.fetchall()
    selected_exam_id = request.args.get('exam_id') or request.form.get('exam_id')
    selected_class_id = request.args.get('class_id') or request.form.get('class_id')
    classes = []
    students = []
    subjects = []
    marks = {}
    published = False
    if selected_exam_id:
        with db.cursor() as cur:
            # Get all classes for this exam
            cur.execute("SELECT DISTINCT s.class_id, c.name FROM students s JOIN classes c ON s.class_id = c.id JOIN marks m ON m.student_id = s.id WHERE m.exam_id=%s ORDER BY c.name", (selected_exam_id,))
            classes = cur.fetchall()
        # If class selected, show results for that class
        if selected_class_id:
            with db.cursor() as cur:
                cur.execute("SELECT * FROM exams WHERE id=%s", (selected_exam_id,))
                exam = cur.fetchone()
                published = bool(exam['published']) if exam else False
                # Get students for this class
                cur.execute("SELECT id, roll_no, name FROM students WHERE class_id=%s ORDER BY roll_no", (selected_class_id,))
                students = cur.fetchall()
                # Get subjects for this class
                cur.execute("SELECT id, name FROM subjects WHERE class_id=%s ORDER BY name", (selected_class_id,))
                subjects = cur.fetchall()
                # Get marks for this exam/class
                cur.execute("SELECT student_id, subject_id, marks, out_of FROM marks WHERE exam_id=%s", (selected_exam_id,))
                for row in cur.fetchall():
                    marks[(row['student_id'], row['subject_id'])] = {'marks': row['marks'], 'out_of': row['out_of']}
            # Handle publish for class
            if request.method == 'POST' and request.form.get('publish') and not published:
                with db.cursor() as cur:
                    cur.execute("UPDATE exams SET published=1 WHERE id=%s", (selected_exam_id,))
                    db.commit()
                flash('Result published for class!', 'success')
                return redirect(url_for('admin_review_results', exam_id=selected_exam_id, class_id=selected_class_id))
    db.close()
    return render_template('admin_review_results.html', exams=exams, classes=classes, students=students, subjects=subjects, marks=marks, selected_exam_id=selected_exam_id, selected_class_id=selected_class_id, published=published)
"""
--- Imports and App Initialization (must be at the top) ---
"""
''
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectMultipleField, SelectField, DateField, FloatField, FieldList, FormField
from wtforms.validators import DataRequired, Email, Length, Optional
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
from config import Config
from datetime import datetime
from functools import wraps
from calendar import monthrange
import pandas as pd
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

''
def student_dashboard():
    """Student dashboard showing attendance and latest (or previous) published exam marks."""
    db = get_db()
    # Get student's internal ID from user_id
    student_id = None
    class_id = None
    with db.cursor() as cur:
        cur.execute("SELECT id, class_id FROM students WHERE user_id=%s", (session['user_id'],))
        student_row = cur.fetchone()
        if student_row:
            student_id = student_row['id']
            class_id = student_row['class_id']
    attendance = []
    defaulter = False
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    # Attendance analytics
    if student_id:
        with db.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT s.id, s.name FROM subjects s 
                JOIN attendance a ON s.id=a.subject_id 
                WHERE a.student_id=%s
                ORDER BY s.name
            """, (student_id,))
            subjects_att = cur.fetchall()
            for subj in subjects_att:
                cur.execute("""
                    SELECT SUM(status='present') as presents, COUNT(id) as total 
                    FROM attendance 
                    WHERE student_id=%s AND subject_id=%s AND DATE_FORMAT(date, '%%Y-%%m')=%s
                """, (student_id, subj['id'], month))
                att = cur.fetchone()
                total_classes = att['total']
                percent = round(100 * att['presents'] / total_classes, 2) if total_classes else 0
                attendance.append({'name': subj['name'], 'percent': percent, 'total': total_classes})
                if percent > 0 and percent < 75:
                    defaulter = True
    # Get all published exams for the student's class, newest first
    published_exams = []
    if student_id:
        with db.cursor() as cur:
            cur.execute("""
                SELECT e.* , c.name as class_name FROM exams e
                JOIN classes c ON c.id = e.class_id
                WHERE e.class_id=%s AND e.published=1
                ORDER BY e.year DESC, e.month DESC, e.id DESC
            """, (class_id,))
            published_exams = cur.fetchall()
    # Find the latest exam with marks, or fallback to previous
    exam_to_show = None
    subjects_to_show = []
    marks_to_show = {}
    if published_exams:
        for exam in published_exams:
            with db.cursor() as cur:
                cur.execute("SELECT id, name FROM subjects WHERE class_id=%s", (exam['class_id'],))
                subjects = cur.fetchall()
                has_marks = False
                for subj in subjects:
                    cur.execute("SELECT marks, out_of FROM marks WHERE exam_id=%s AND student_id=%s AND subject_id=%s", (exam['id'], student_id, subj['id']))
                    m = cur.fetchone()
                    if m:
                        marks_to_show[subj['id']] = m
                        has_marks = True
                if has_marks:
                    exam_to_show = exam
                    subjects_to_show = subjects
                    break
    # Get student name for navbar
    student_name = None
    with db.cursor() as cur:
        cur.execute("SELECT name FROM users WHERE id=%s", (session['user_id'],))
        row = cur.fetchone()
        if row:
            student_name = row['name']
    # Check today's attendance for each subject
    from datetime import date
    today_str = date.today().strftime('%Y-%m-%d')
    todays_attendance = []
    if student_id:
        with db.cursor() as cur:
            cur.execute("SELECT s.name, a.status FROM subjects s LEFT JOIN attendance a ON s.id=a.subject_id AND a.student_id=%s AND a.date=%s WHERE s.class_id=%s", (student_id, today_str, class_id))
            for row in cur.fetchall():
                todays_attendance.append({'subject': row['name'], 'status': row['status']})
    db.close()
    return render_template('student_dashboard.html', attendance=attendance, month=month, defaulter=defaulter, student_name=student_name, latest_exam=exam_to_show, latest_subjects=subjects_to_show, latest_marks=marks_to_show, todays_attendance=todays_attendance)

# from reportlab.pdfgen import canvas (already imported above)

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])

class FacultyAssignmentForm(FlaskForm):
    class_id = SelectField('Class', coerce=int, validators=[DataRequired()])
    division_id = SelectField('Division', coerce=int, validators=[DataRequired()])
    subject_id = SelectField('Subject', coerce=int, validators=[DataRequired()])

class FacultyForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    assignments = FieldList(FormField(FacultyAssignmentForm), min_entries=1)

# --- Minimal Form Definitions to Fix Errors ---
class SubjectForm(FlaskForm):
    name = StringField('Subject Name', validators=[DataRequired()])
    class_id = SelectField('Class', coerce=int, validators=[DataRequired()])

class StudentForm(FlaskForm):
    roll_no = StringField('Roll No', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional()])
    class_id = SelectField('Class', coerce=int, validators=[DataRequired()])
    division_id = SelectField('Division', coerce=int, validators=[DataRequired()])

class AttendanceForm(FlaskForm):
    subject = SelectField('Subject', coerce=int, validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])

class MarksForm(FlaskForm):
    subject = SelectField('Subject', coerce=int, validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])

class ProfileForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Optional(), Length(min=6)])

# --- Exam Management Models and DB Migration ---
def create_exams_table():
    db = get_db()
    with db.cursor() as cur:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS exams (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                year INT NOT NULL,
                month INT NOT NULL,
                class_id INT NOT NULL,
                published BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (class_id) REFERENCES classes(id)
            ) ENGINE=InnoDB;
        ''')
        # Add exam_id to marks table if not exists
        cur.execute("""
            ALTER TABLE marks ADD COLUMN IF NOT EXISTS exam_id INT,
            ADD FOREIGN KEY (exam_id) REFERENCES exams(id)
        """)
    db.commit()
    db.close()

# ...existing code...


def get_db():
    """Establishes and returns a new MySQL database connection."""
    return pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        db=app.config['MYSQL_DB'],
        cursorclass=pymysql.cursors.DictCursor
    )


def login_required(role=None):
    """Decorator to ensure user is logged in and optionally has a specific role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                flash('Unauthorized access', 'danger')
                return redirect(url_for('home')) # Redirect to appropriate dashboard or login
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# --- Faculty: Enter Marks for Exams (with Class, Division, Subject, Exam, Out Of) ---
@app.route('/faculty/exam_marks', methods=['GET', 'POST'])
@login_required('faculty')
def faculty_exam_marks():
    db = get_db()
    user_id = session['user_id']
    # Get all assignments for this faculty
    selected_class_id = request.args.get('class_id') or request.form.get('class_id') or None
    selected_division_id = request.args.get('division_id') or request.form.get('division_id') or None
    with db.cursor() as cur:
        cur.execute("SELECT DISTINCT class_id FROM faculty_assignments WHERE faculty_user_id=%s", (user_id,))
        class_ids = [row['class_id'] for row in cur.fetchall()]
        if class_ids:
            cur.execute("SELECT id, name FROM classes WHERE id IN (%s)" % (','.join(str(cid) for cid in class_ids)))
            classes = cur.fetchall()
        else:
            classes = []
        divisions = []
        selected_class_id_int = int(selected_class_id) if selected_class_id else None
        if selected_class_id_int:
            cur.execute("""
                SELECT d.id, d.name FROM class_divisions cd
                JOIN divisions d ON cd.division_id = d.id
                WHERE cd.class_id = %s
            """, (selected_class_id_int,))
            divisions = cur.fetchall()
    selected_class_id = request.args.get('class_id') or request.form.get('class_id') or None
    selected_division_id = request.args.get('division_id') or request.form.get('division_id') or None
    selected_subject_id = request.args.get('subject_id') or request.form.get('subject_id')
    selected_exam_id = request.args.get('exam_id') or request.form.get('exam_id')
    out_of = request.form.get('out_of') or request.args.get('out_of')
    subjects = []
    exams = []
    students = []
    marks = {}
    if selected_class_id and selected_division_id:
        with db.cursor() as cur:
            # Get subjects for this faculty/class/division
            cur.execute("""
                SELECT s.id, s.name FROM faculty_assignments fa
                JOIN subjects s ON fa.subject_id = s.id
                WHERE fa.faculty_user_id=%s AND fa.class_id=%s AND fa.division_id=%s
                ORDER BY s.name
            """, (user_id, selected_class_id, selected_division_id))
            subjects = cur.fetchall()
            # Get exams for this class
            cur.execute("SELECT e.*, c.name as class_name FROM exams e JOIN classes c ON e.class_id = c.id WHERE e.class_id=%s ORDER BY e.year DESC, e.month DESC, e.name", (selected_class_id,))
            exams = cur.fetchall()
        if selected_subject_id and selected_exam_id:
            with db.cursor() as cur:
                # Get students for this class/division
                cur.execute("SELECT id, roll_no, name FROM students WHERE class_id=%s AND division_id=%s ORDER BY roll_no", (selected_class_id, selected_division_id))
                students = cur.fetchall()
                # Get any existing marks for this exam/subject
                cur.execute("SELECT student_id, marks FROM marks WHERE exam_id=%s AND subject_id=%s", (selected_exam_id, selected_subject_id))
                for row in cur.fetchall():
                    marks[row['student_id']] = row['marks']
            if request.method == 'POST':
                out_of_val = request.form.get('out_of')
                with db.cursor() as cur:
                    for student in students:
                        marks_val = request.form.get(f"marks_{student['id']}")
                        if marks_val is not None and marks_val != '':
                            cur.execute("SELECT id FROM marks WHERE student_id=%s AND exam_id=%s AND subject_id=%s", (student['id'], selected_exam_id, selected_subject_id))
                            row = cur.fetchone()
                            if row:
                                cur.execute("UPDATE marks SET marks=%s, out_of=%s WHERE id=%s", (marks_val, out_of_val, row['id']))
                            else:
                                cur.execute("INSERT INTO marks (student_id, exam_id, subject_id, marks, out_of, recorded_by) VALUES (%s, %s, %s, %s, %s, %s)", (student['id'], selected_exam_id, selected_subject_id, marks_val, out_of_val, user_id))
                    db.commit()
                flash('Marks saved successfully!', 'success')
                return redirect(url_for('faculty_exam_marks', class_id=selected_class_id, division_id=selected_division_id, subject_id=selected_subject_id, exam_id=selected_exam_id, out_of=out_of_val))
    db.close()
    return render_template('faculty_exam_marks.html', classes=classes, divisions=divisions, subjects=subjects, exams=exams, students=students, marks=marks, selected_class_id=selected_class_id, selected_division_id=selected_division_id, selected_subject_id=selected_subject_id, selected_exam_id=selected_exam_id, out_of=out_of)

# --- Admin: Manage Exams ---
@app.route('/admin/exams', methods=['GET', 'POST'])
@login_required('admin')
def admin_manage_exams():
    db = get_db()
    # Get all classes for dropdown
    with db.cursor() as cur:
        cur.execute("SELECT id, name FROM classes ORDER BY name")
        classes = cur.fetchall()
    # Add new exam
    if request.method == 'POST':
        name = request.form['name']
        year = int(request.form['year'])
        month = int(request.form['month'])
        class_ids = request.form.getlist('class_id')
        valid_class_ids = [cid for cid in class_ids if cid.isdigit()]
        if not valid_class_ids:
            flash('Please select at least one valid class.', 'danger')
            return redirect(url_for('admin_manage_exams'))
        with db.cursor() as cur:
            for cid in valid_class_ids:
                cur.execute("INSERT INTO exams (name, year, month, class_id) VALUES (%s, %s, %s, %s)",
                            (name, year, month, int(cid)))
        db.commit()
        flash('Exam added successfully for selected class(es)!', 'success')
        return redirect(url_for('admin_manage_exams'))
    # List all exams with class name
    with db.cursor() as cur:
        cur.execute("""
            SELECT e.*, c.name as class_name FROM exams e
            JOIN classes c ON e.class_id = c.id
            ORDER BY e.year DESC, e.month DESC, e.name
        """)
        exams = cur.fetchall()
    db.close()
    from datetime import datetime
    now = datetime.now()
    return render_template('admin_exams.html',
        classes=classes,
        exams=exams,
        current_year=now.year,
        current_month=now.month
    )

# --- Attendance Register (Admin & Faculty) ---

@app.route('/admin/attendance_register', methods=['GET'])
@login_required('admin')
def admin_attendance_register():
    return attendance_register(role='admin')

@app.route('/faculty/attendance_register', methods=['GET'])
@login_required('faculty')
def faculty_attendance_register():
    return attendance_register(role='faculty')

def attendance_register(role):
    db = get_db()
    user_id = session['user_id']
    # Get filter options
    with db.cursor() as cur:
        cur.execute("SELECT id, name FROM classes ORDER BY name")
        classes = cur.fetchall()
        # Filter divisions: if class selected, show only assigned divisions
        class_id_int = int(request.args.get('class_id')) if request.args.get('class_id') and request.args.get('class_id').isdigit() else None
        if class_id_int:
            cur.execute("""
                SELECT d.id, d.name FROM class_divisions cd
                JOIN divisions d ON cd.division_id = d.id
                WHERE cd.class_id = %s
                ORDER BY d.name
            """, (class_id_int,))
            divisions = cur.fetchall()
        else:
            cur.execute("SELECT id, name FROM divisions ORDER BY name")
            divisions = cur.fetchall()
        # Subjects: filter by class/division if selected
        subjects = []
        division_id = request.args.get('division_id')
        if class_id_int and division_id and division_id.isdigit():
            division_id_int = int(division_id)
            if role == 'admin':
                cur.execute("SELECT id, name, class_id FROM subjects WHERE class_id=%s ORDER BY name", (class_id_int,))
                subjects = cur.fetchall()
            else:
                cur.execute("""
                    SELECT s.id, s.name, fa.class_id, fa.division_id FROM faculty_assignments fa
                    JOIN subjects s ON fa.subject_id = s.id
                    WHERE fa.faculty_user_id = %s AND fa.class_id = %s AND fa.division_id = %s
                    GROUP BY s.id, s.name, fa.class_id, fa.division_id ORDER BY s.name
                """, (user_id, class_id_int, division_id_int))
                subjects = cur.fetchall()
        else:
            subjects = []

        # Build class_subjects: {"classid-divisionid": [subjects]}
        class_subjects = {}
        # For admin, build for all class/division combinations
        if role == 'admin':
            cur.execute("SELECT cd.class_id, cd.division_id, s.id as subject_id, s.name as subject_name FROM class_divisions cd JOIN subjects s ON cd.class_id = s.class_id")
            rows = cur.fetchall()
            for row in rows:
                key = f"{row['class_id']}-{row['division_id']}"
                class_subjects.setdefault(key, []).append({'id': row['subject_id'], 'name': row['subject_name']})
        else:
            # For faculty, build only for assigned class/division
            cur.execute("""
                SELECT fa.class_id, fa.division_id, s.id as subject_id, s.name as subject_name FROM faculty_assignments fa JOIN subjects s ON fa.subject_id = s.id WHERE fa.faculty_user_id = %s
            """, (user_id,))
            rows = cur.fetchall()
            for row in rows:
                key = f"{row['class_id']}-{row['division_id']}"
                class_subjects.setdefault(key, []).append({'id': row['subject_id'], 'name': row['subject_name']})

    # Get filters from request
    class_id = request.args.get('class_id')
    division_id = request.args.get('division_id')
    subject_id = request.args.get('subject_id')
    month = request.args.get('month')
    today = datetime.today()
    if not month:
        month = today.strftime('%Y-%m')
    year, month_num = [int(x) for x in month.split('-')]
    num_days = monthrange(year, month_num)[1]
    dates = [datetime(year, month_num, d+1) for d in range(num_days)]
    date_strs = [d.strftime('%Y-%m-%d') for d in dates]

    students = []
    attendance = {}
    totals = {}
    can_edit = (role == 'admin') or (role == 'faculty')
    if class_id and division_id and subject_id:
        with db.cursor() as cur:
            cur.execute("""
                SELECT st.id, st.roll_no, st.name FROM students st
                WHERE st.class_id=%s AND st.division_id=%s
                ORDER BY st.roll_no
            """, (class_id, division_id))
            students = cur.fetchall()
            # Get attendance for all students for this subject/month
            cur.execute("""
                SELECT student_id, date, status FROM attendance
                WHERE subject_id=%s AND date BETWEEN %s AND %s
            """, (subject_id, f"{month}-01", f"{month}-{num_days:02d}"))
            att_rows = cur.fetchall()
            # Build attendance dict: attendance[student_id][date] = 'present'/'absent'
            attendance = {s['id']: {d: '' for d in date_strs} for s in students}
            for row in att_rows:
                attendance[row['student_id']][row['date'].strftime('%Y-%m-%d')] = row['status']
            # Totals
            totals = {s['id']: sum(1 for d in date_strs if attendance[s['id']][d] == 'present') for s in students}

    # Build class->divisions mapping for JS filtering
    with db.cursor() as cur:
        cur.execute("SELECT id, name FROM divisions ORDER BY name")
        all_divisions = cur.fetchall()
        cur.execute("SELECT class_id, division_id FROM class_divisions")
        class_div_rows = cur.fetchall()
        class_divisions = {c['id']: [] for c in classes}
        div_dict = {d['id']: d for d in all_divisions}
        for row in class_div_rows:
            if row['class_id'] in class_divisions and row['division_id'] in div_dict:
                class_divisions[row['class_id']].append(div_dict[row['division_id']])
    db.close()
    return render_template('attendance_register.html',
        role=role,
        classes=classes,
        divisions=divisions,
        subjects=subjects,
        students=students,
        attendance=attendance,
        totals=totals,
        dates=[{'iso': d, 'day': int(d[-2:])} for d in date_strs],
        selected_class_id=class_id,
        selected_division_id=division_id,
        selected_subject_id=subject_id,
        selected_month=month,
        can_edit=can_edit,
        class_divisions=class_divisions
            ,class_subjects=class_subjects
    )

# AJAX endpoint to update attendance
@app.route('/update_attendance_ajax', methods=['POST'])
@login_required()
def update_attendance_ajax():
    data = request.get_json()
    student_id = data['student_id']
    date = data['date']
    status = data['status']
    subject_id = data['subject_id']
    db = get_db()
    with db.cursor() as cur:
        # Upsert attendance
        cur.execute("""
            SELECT id FROM attendance WHERE student_id=%s AND subject_id=%s AND date=%s
        """, (student_id, subject_id, date))
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE attendance SET status=%s, recorded_by=%s WHERE id=%s", (status, session['user_id'], row['id']))
        else:
            cur.execute("INSERT INTO attendance (student_id, subject_id, status, date, recorded_by) VALUES (%s, %s, %s, %s, %s)",
                        (student_id, subject_id, status, date, session['user_id']))
        db.commit()
    db.close()
    return jsonify({'success': True})



# --- General Routes ---

# --- Forgot Password Feature ---
from flask import current_app
import smtplib, ssl, random, string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])

otp_store = {}

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    otp_sent = False
    # First form: send OTP
    if form.validate_on_submit() and 'otp' not in request.form:
        email = form.email.data
        otp = ''.join(random.choices(string.digits, k=6))
        otp_store[email] = otp
        send_otp_email(email, otp)
        otp_sent = True
        flash('OTP sent to your email.', 'info')
        return render_template('forgot_password.html', form=form, otp_sent=otp_sent)

    # Second form: verify OTP and reset password
    if request.method == 'POST' and 'otp' in request.form and 'new_password' in request.form:
        email = request.form.get('email')
        otp = request.form.get('otp')
        from werkzeug.security import generate_password_hash
        new_password = request.form.get('new_password')
        hashed_password = generate_password_hash(new_password)
        if otp_store.get(email) == otp:
            db = get_db()
            with db.cursor() as cur:
                cur.execute("UPDATE users SET password=%s WHERE email=%s", (hashed_password, email))
            db.commit()
            db.close()
            otp_store.pop(email, None)
            flash('Password reset successful. Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid OTP.', 'danger')
            otp_sent = True
        # Re-render with OTP form
        return render_template('forgot_password.html', form=form, otp_sent=otp_sent)

    return render_template('forgot_password.html', form=form, otp_sent=otp_sent)

def send_otp_email(to_email, otp):
    user = current_app.config['EMAIL_USER']
    password = current_app.config['EMAIL_PASS']
    msg = MIMEMultipart()
    msg['From'] = user
    msg['To'] = to_email
    msg['Subject'] = 'Your OTP for Password Reset'
    body = f'Your OTP for password reset is: {otp}'
    msg.attach(MIMEText(body, 'plain'))
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
            server.login(user, password)
            server.sendmail(user, to_email, msg.as_string())
        print(f"OTP email sent to {to_email}")
    except Exception as e:
        print(f"Error sending OTP email: {e}")
        from flask import flash
        flash(f"Error sending OTP email: {e}", "danger")

@app.route('/')
def home():
    """Show the academic website home page."""
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    form = LoginForm()
    if form.validate_on_submit():
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email=%s", (form.email.data,))
            user = cur.fetchone()
            if user and check_password_hash(user['password'], form.password.data):
                session['user_id'] = user['id']
                session['role'] = user['role']
                session['user_name'] = user['name']
                flash('Login successful', 'success')
                return redirect(url_for('home'))
            else:
                flash('Invalid credentials', 'danger')
        db.close()
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    """Logs out the user."""
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('login'))

# --- Admin Routes ---

@app.route('/admin')
@login_required('admin')
def admin_dashboard():
    """Admin dashboard showing system overview statistics."""
    db = get_db()
    with db.cursor() as cur:
        # Count total faculties
        cur.execute("SELECT COUNT(*) as total FROM users WHERE role='faculty'")
        total_faculties = cur.fetchone()['total']
        # Count total students
        cur.execute("SELECT COUNT(*) as total FROM students")
        total_students = cur.fetchone()['total']
        # Count total subjects
        cur.execute("SELECT COUNT(*) as total FROM subjects")
        total_subjects = cur.fetchone()['total']
    db.close()
    return render_template('admin_dashboard.html', total_faculties=total_faculties, total_students=total_students, total_subjects=total_subjects)


@app.route('/admin/classes', methods=['GET', 'POST'])
@login_required('admin')
def admin_classes():
    """Admin route to add/manage classes and divisions."""
    db = get_db()
    if request.method == 'POST':
        if 'add_division' in request.form:
            # Handle adding a new division
            new_div = request.form.get('new_division')
            if new_div:
                try:
                    with db.cursor() as cur:
                        cur.execute("INSERT INTO divisions (name) VALUES (%s)", (new_div,))
                        db.commit()
                    flash(f'Division "{new_div}" added', 'success')
                except pymysql.err.IntegrityError:
                    flash('Division already exists', 'warning')
        else:
            # Handle adding a new class
            name = request.form.get('name')
            selected_divisions = request.form.getlist('divisions')
            if name and selected_divisions:
                try:
                    with db.cursor() as cur:
                        # Check if class already exists
                        cur.execute("SELECT id FROM classes WHERE name=%s", (name,))
                        row = cur.fetchone()
                        if row:
                            class_id = row['id']
                        else:
                            cur.execute("INSERT INTO classes (name) VALUES (%s)", (name,))
                            class_id = cur.lastrowid
                        added = 0
                        for div_id in selected_divisions:
                            cur.execute("SELECT 1 FROM class_divisions WHERE class_id=%s AND division_id=%s", (class_id, div_id))
                            exists = cur.fetchone()
                            if not exists:
                                cur.execute("INSERT INTO class_divisions (class_id, division_id) VALUES (%s, %s)", (class_id, div_id))
                                added += 1
                        db.commit()
                    if added:
                        flash(f'Divisions added to class "{name}"', 'success')
                    else:
                        flash('All selected divisions already assigned to this class.', 'warning')
                except pymysql.err.IntegrityError:
                    flash('Error adding class or division assignment.', 'danger')
            else:
                flash('Please provide class name and select at least one division.', 'danger')

    with db.cursor() as cur:
        # Get all divisions for the form
        cur.execute("SELECT id, name FROM divisions")
        divisions = cur.fetchall()
        # Get all classes with their divisions
        cur.execute("SELECT c.id, c.name, GROUP_CONCAT(d.name SEPARATOR ', ') as divisions FROM classes c LEFT JOIN class_divisions cd ON c.id=cd.class_id LEFT JOIN divisions d ON cd.division_id=d.id GROUP BY c.id ORDER BY c.name")
        classes = cur.fetchall()
    db.close()
    return render_template('admin_classes.html', classes=classes, divisions=divisions)


@app.route('/admin/divisions', methods=['GET', 'POST'])
@login_required('admin')
def admin_divisions():
    """Admin route to manage divisions (used if division management is separate)."""
    db = get_db()
    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            try:
                with db.cursor() as cur:
                    cur.execute("INSERT INTO divisions (name) VALUES (%s)", (name,))
                    db.commit()
                flash('Division added', 'success')
            except pymysql.err.IntegrityError:
                flash('Division already exists', 'warning')

    with db.cursor() as cur:
        cur.execute("SELECT * FROM divisions ORDER BY name")
        divisions = cur.fetchall()
    db.close()
    return render_template('admin_divisions.html', divisions=divisions)


@app.route('/admin/class/<int:class_id>/subjects', methods=['GET', 'POST'])
@login_required('admin')
def admin_class_subjects(class_id):
    """Admin route to manage subjects for a specific class."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT name FROM classes WHERE id=%s", (class_id,))
        class_row = cur.fetchone()
        class_name = class_row['name'] if class_row else 'Unknown'

        if request.method == 'POST':
            # Handle Add subject
            subject_name = request.form.get('subject_name')
            if subject_name:
                try:
                    cur.execute("INSERT INTO subjects (name, class_id) VALUES (%s, %s)", (subject_name, class_id))
                    db.commit()
                    flash('Subject added', 'success')
                except pymysql.err.IntegrityError:
                    flash('Subject already exists for this class', 'warning')

        # Handle Delete subject
        del_id = request.args.get('delete')
        if del_id:
            cur.execute("DELETE FROM subjects WHERE id=%s AND class_id=%s", (del_id, class_id))
            db.commit()
            flash('Subject deleted', 'info')

        cur.execute("SELECT id, name FROM subjects WHERE class_id=%s ORDER BY name", (class_id,))
        subjects = cur.fetchall()
    db.close()
    return render_template('admin_class_subjects.html', class_id=class_id, class_name=class_name, subjects=subjects)


@app.route('/admin/add_faculty', methods=['GET', 'POST'])
@login_required('admin')
def add_faculty():
    """Admin route to add a new faculty user and assign their subjects/classes/divisions."""
    db = get_db()
    form = FacultyForm()
    with db.cursor() as cur:
        # Fetch necessary data for the form dropdowns
        cur.execute("SELECT id, name FROM classes ORDER BY name")
        classes = cur.fetchall()
        cur.execute("SELECT id, name FROM divisions ORDER BY name")
        all_divisions = cur.fetchall()
        cur.execute("SELECT id, name, class_id FROM subjects ORDER BY name")
        all_subjects = cur.fetchall()
        # Build class->divisions mapping using class_divisions table
        cur.execute("SELECT class_id, division_id FROM class_divisions")
        class_div_rows = cur.fetchall()
        class_divisions = {c['id']: [] for c in classes}
        div_dict = {d['id']: d for d in all_divisions}
        for row in class_div_rows:
            if row['class_id'] in class_divisions and row['division_id'] in div_dict:
                class_divisions[row['class_id']].append(div_dict[row['division_id']])
        # Build class->subjects mapping
        class_subjects = {c['id']: [s for s in all_subjects if s['class_id'] == c['id']] for c in classes}
        # Set choices for all assignment fields (Needed for WTForms rendering)
        class_choices = [(0, 'Select Class')] + [(c['id'], c['name']) for c in classes]
        division_choices = [(0, 'Select Division')] + [(d['id'], d['name']) for d in all_divisions]
        subject_choices = [(0, 'Select Subject')] + [(s['id'], s['name']) for s in all_subjects]
        for assignment_form in form.assignments:
            assignment_form.class_id.choices = class_choices
            assignment_form.division_id.choices = division_choices
            assignment_form.subject_id.choices = subject_choices
        if form.validate_on_submit():
            print('Faculty form data:', form.data)
            # Check that at least one assignment is valid (all fields selected)
            valid_assignments = [a for a in form.assignments.data if a['class_id'] and a['division_id'] and a['subject_id']]
            if not valid_assignments:
                flash('Please add at least one valid assignment (class, division, subject).', 'danger')
                print('No valid assignments, aborting faculty add.')
            else:
                hashed_pw = generate_password_hash(form.password.data)
                try:
                    cur.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, 'faculty')", 
                                (form.name.data, form.email.data, hashed_pw))
                    faculty_id = cur.lastrowid
                    print(f"DEBUG: User inserted successfully. Faculty ID: {faculty_id}")
                    for i, assignment in enumerate(valid_assignments):
                        cur.execute("""
                            INSERT INTO faculty_assignments 
                            (faculty_user_id, subject_id, class_id, division_id) 
                            VALUES (%s, %s, %s, %s)
                        """, (faculty_id, assignment['subject_id'], assignment['class_id'], assignment['division_id']))
                        print(f"DEBUG: Assignment {i+1} Inserted: Subject {assignment['subject_id']}, Class {assignment['class_id']}, Division {assignment['division_id']}")
                    db.commit()
                    print("DEBUG: All changes committed to DB.")
                    flash('Faculty added and assignments recorded', 'success')
                    return redirect(url_for('admin_dashboard'))
                except pymysql.err.IntegrityError as e:
                    db.rollback() 
                    error_message = str(e)
                    print(f"ERROR: IntegrityError occurred. Details: {error_message}")
                    if "Duplicate entry" in error_message and "email" in error_message:
                        flash('Email already exists. Please use a different email.', 'danger')
                    elif "Duplicate entry" in error_message and "faculty_user_id" in error_message and "subject_id" in error_message:
                        flash('Error: You tried to assign the same subject/class/division combination twice to this faculty member.', 'danger')
                    else:
                        flash('An error occurred during faculty assignment (e.g., duplicate assignment or invalid foreign key).', 'danger')
                except Exception as e:
                    db.rollback()
                    print(f"FATAL ERROR: Unexpected error occurred: {str(e)}")
                    flash(f'An unexpected error occurred: {str(e)}', 'danger')
        else:
            print("--- DEBUG: Form Validation FAILED ---")
            print("Form Errors:", form.errors)
            non_assignment_errors = {k: v for k, v in form.errors.items() if k != 'assignments'}
            if non_assignment_errors:
                flash(f'Form submission failed for Name, Email, or Password.', 'danger')

    db.close()
    return render_template('add_faculty.html', form=form, classes=classes, divisions=all_divisions, subjects=all_subjects, class_divisions=class_divisions, class_subjects=class_subjects)


@app.route('/admin/add_subject', methods=['GET', 'POST'])
@login_required('admin')
def add_subject():
    """Admin route to add a subject and link it to a class."""
    form = SubjectForm()
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT id, name FROM classes ORDER BY name")
        classes = cur.fetchall()
        form.class_id.choices = [(c['id'], c['name']) for c in classes]
        if form.validate_on_submit():
            try:
                cur.execute("INSERT INTO subjects (name, class_id) VALUES (%s, %s)", (form.name.data, form.class_id.data))
                db.commit()
                flash('Subject added', 'success')
                return redirect(url_for('admin_dashboard'))
            except pymysql.err.IntegrityError:
                flash('Subject already exists for this class or class is invalid.', 'warning')
    db.close()
    return render_template('add_subject.html', form=form)


@app.route('/admin/faculties')
@login_required('admin')
def admin_faculties():
    """
    Admin route to view all faculties and their assignments.
    FIXED: Uses faculty_assignments table instead of non-existent faculty_subjects.
    """
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT id, name, email FROM users WHERE role='faculty' ORDER BY name")
        faculties_raw = cur.fetchall()
        faculties = []
        for faculty in faculties_raw:
            faculty_id = int(faculty['id'])
            # Query the correct table (faculty_assignments) and join with subjects, classes, divisions
            cur.execute("""
                SELECT s.name as subject_name, c.name as class_name, d.name as division_name
                FROM faculty_assignments fa
                JOIN subjects s ON fa.subject_id=s.id
                JOIN classes c ON fa.class_id=c.id
                JOIN divisions d ON fa.division_id=d.id
                WHERE fa.faculty_user_id=%s
                ORDER BY c.name, d.name, s.name
            """, (faculty_id,))
            assignments = cur.fetchall()
            faculties.append({
                'id': faculty_id,
                'name': faculty['name'],
                'email': faculty['email'],
                'assignments': assignments
            })
    db.close()
    return render_template('admin_faculties.html', faculties=faculties)


@app.route('/admin/students')
@login_required('admin')
def admin_students():
    """Admin route to view and filter students."""
    db = get_db()
    class_id = request.args.get('class_id', type=int)
    division_id = request.args.get('division_id', type=int)
    with db.cursor() as cur:
        cur.execute("SELECT id, name FROM classes ORDER BY name")
        classes = cur.fetchall()
        # Filter divisions: if class selected, show only assigned divisions
        if class_id:
            cur.execute("""
                SELECT d.id, d.name FROM class_divisions cd
                JOIN divisions d ON cd.division_id = d.id
                WHERE cd.class_id = %s
                ORDER BY d.name
            """, (class_id,))
            divisions = cur.fetchall()
        else:
            cur.execute("SELECT id, name FROM divisions ORDER BY name")
            divisions = cur.fetchall()
        query = '''
            SELECT st.roll_no, u.name, u.email, c.name as class_name, d.name as division_name 
            FROM students st 
            JOIN users u ON st.user_id=u.id 
            JOIN classes c ON st.class_id=c.id
            JOIN divisions d ON st.division_id=d.id
            WHERE 1=1
        '''
        params = []
        if class_id:
            query += " AND st.class_id=%s"
            params.append(class_id)
        if division_id:
            query += " AND st.division_id=%s"
            params.append(division_id)
        query += " ORDER BY st.roll_no"
        cur.execute(query, params)
        students = cur.fetchall()
    db.close()
    return render_template('admin_students.html', students=students, classes=classes, divisions=divisions, selected_class_id=class_id, selected_division_id=division_id)

@app.route('/admin/defaulters')
@login_required('admin')
def admin_defaulters():
    """Admin route to view attendance defaulters across the system."""
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    threshold_arg = request.args.get('threshold', '75')
    class_id = request.args.get('class_id', type=int)
    division_id = request.args.get('division_id', type=int)
    try:
        threshold = float(threshold_arg) if threshold_arg.strip() else 75.0
    except ValueError:
        threshold = 75.0
    db = get_db()
    with db.cursor() as cur:
        # Get all classes/divisions assigned (for admin: all, for faculty: only assigned)
        cur.execute("SELECT id, name FROM classes ORDER BY name")
        classes = cur.fetchall()
        if class_id:
            cur.execute("""
                SELECT d.id, d.name FROM class_divisions cd
                JOIN divisions d ON cd.division_id = d.id
                WHERE cd.class_id = %s
                ORDER BY d.name
            """, (class_id,))
            divisions = cur.fetchall()
        else:
            cur.execute("SELECT id, name FROM divisions ORDER BY name")
            divisions = cur.fetchall()
        # Defaulter query with optional class/division filter
        query = '''
            SELECT st.id as student_id, st.roll_no, u.name as student, s.name as subject,
            ROUND(100*SUM(a.status='present')/COUNT(a.id),2) as percent,
            COUNT(a.id) as total_classes
            FROM attendance a
            JOIN students st ON a.student_id=st.id
            JOIN users u ON st.user_id=u.id
            JOIN subjects s ON a.subject_id=s.id
            WHERE DATE_FORMAT(a.date, '%%Y-%%m')=%s
        '''
        params = [month]
        if class_id:
            query += ' AND st.class_id=%s'
            params.append(class_id)
        if division_id:
            query += ' AND st.division_id=%s'
            params.append(division_id)
        query += ''' GROUP BY st.id, a.subject_id HAVING percent < %s ORDER BY percent DESC '''
        params.append(threshold)
        cur.execute(query, params)
        defaulters = cur.fetchall()
    db.close()
    return render_template('defaulters.html', defaulters=defaulters, month=month, threshold=threshold, classes=classes, divisions=divisions, selected_class_id=class_id, selected_division_id=division_id)


# --- Faculty Routes ---

@app.route('/faculty')
@login_required('faculty')
def faculty_dashboard():
    """
    Faculty dashboard showing their assigned subjects/classes/divisions.
    FIXED: Uses faculty_assignments table instead of non-existent faculty_subjects.
    """
    db = get_db()
    with db.cursor() as cur:
        # Query the correct table (faculty_assignments) and join with subjects, classes, divisions
        cur.execute("""
            SELECT s.name as subject_name, c.name as class_name, d.name as division_name
            FROM faculty_assignments fa
            JOIN subjects s ON fa.subject_id=s.id
            JOIN classes c ON fa.class_id=c.id
            JOIN divisions d ON fa.division_id=d.id
            WHERE fa.faculty_user_id=%s
            ORDER BY c.name, d.name, s.name
        """, (session['user_id'],))
        # Note: 'subjects' now contains assignment details: name, class_name, division_name
        subjects = cur.fetchall()
    db.close()
    # Note: faculty_dashboard.html will need a minor update to iterate over assignment details
    return render_template('faculty_dashboard.html', subjects=subjects)


@app.route('/faculty/add_student', methods=['GET', 'POST'])
@login_required('faculty')
def add_student():
    """Faculty route to add a new student."""
    form = StudentForm()
    db = get_db()
    with db.cursor() as cur:
        # Get all assignments for this faculty
        cur.execute("""
            SELECT fa.class_id, c.name as class_name, fa.division_id, d.name as division_name
            FROM faculty_assignments fa
            JOIN classes c ON fa.class_id = c.id
            JOIN divisions d ON fa.division_id = d.id
            WHERE fa.faculty_user_id = %s
            GROUP BY fa.class_id, fa.division_id
            ORDER BY c.name, d.name
        """, (session['user_id'],))
        assignments = cur.fetchall()
        # Build choices for classes and divisions
        class_choices = []
        division_choices = []
        class_ids = set()
        division_ids = set()
        for a in assignments:
            if a['class_id'] not in class_ids:
                class_choices.append((a['class_id'], a['class_name']))
                class_ids.add(a['class_id'])
            if a['division_id'] not in division_ids:
                division_choices.append((a['division_id'], a['division_name']))
                division_ids.add(a['division_id'])
        form.class_id.choices = class_choices
        form.division_id.choices = division_choices
        if form.validate_on_submit():
            try:
                # 1. Insert into users table
                # Default password is roll_no (hashed) - you can change this logic
                from werkzeug.security import generate_password_hash
                hashed_pw = generate_password_hash(form.roll_no.data)
                cur.execute("""
                    INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, 'student')
                """, (form.name.data, form.email.data, hashed_pw))
                user_id = cur.lastrowid
                # 2. Insert into students table with user_id
                cur.execute("""
                    INSERT INTO students (roll_no, name, email, phone, class_id, division_id, user_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (form.roll_no.data, form.name.data, form.email.data, form.phone.data, form.class_id.data, form.division_id.data, user_id))
                db.commit()
                flash('Student added successfully. Login email: %s, password: %s' % (form.email.data, form.roll_no.data), 'success')
                return redirect(url_for('faculty_dashboard'))
            except pymysql.err.IntegrityError as e:
                db.rollback()
                if "roll_no" in str(e):
                    flash('Roll No already exists.', 'danger')
                elif "email" in str(e):
                    flash('Email already exists.', 'danger')
                else:
                    flash('An integrity error occurred (e.g., duplicate roll no or email).', 'danger')
    db.close()
    return render_template('add_student.html', form=form)


@app.route('/faculty/enter_attendance', methods=['GET', 'POST'])
@login_required('faculty')
def enter_attendance():
    """Faculty route to record attendance for their assigned classes/subjects."""
    db = get_db()
    form = AttendanceForm()
    students = []
    assigned_classes = []
    assigned_divisions = []
    filtered_subjects = []
    class_divisions = {}
    class_subjects = {}
    selected_class_id = request.form.get('class_id') or None
    selected_division_id = request.form.get('division_id') or None

    with db.cursor() as cur:
        # Get all assignments for this faculty
        cur.execute("""
            SELECT fa.subject_id as subject_id, s.name as subject_name, fa.class_id, c.name as class_name, fa.division_id, d.name as division_name
            FROM faculty_assignments fa
            JOIN subjects s ON fa.subject_id = s.id
            JOIN classes c ON fa.class_id = c.id
            JOIN divisions d ON fa.division_id = d.id
            WHERE fa.faculty_user_id = %s
            ORDER BY c.name, d.name, s.name
        """, (session['user_id'],))
        assignments = cur.fetchall()

        # Build assigned_classes and assigned_divisions (unique)
        class_set = {}
        division_set = {}
        for a in assignments:
            class_set[a['class_id']] = a['class_name']
            division_set[a['division_id']] = a['division_name']
        assigned_classes = [{'id': cid, 'name': cname} for cid, cname in class_set.items()]
        assigned_divisions = [{'id': did, 'name': dname} for did, dname in division_set.items()]

        # Build class_divisions: {class_id: [divisions]}
        for a in assignments:
            class_divisions.setdefault(str(a['class_id']), []).append({'id': a['division_id'], 'name': a['division_name']})
        # Build class_subjects: {"classid-divisionid": [subjects]}
        for a in assignments:
            key = f"{a['class_id']}-{a['division_id']}"
            class_subjects.setdefault(key, []).append({'id': a['subject_id'], 'name': a['subject_name']})

        # Filter subjects for selected class/division
        if selected_class_id and selected_division_id:
            filtered_subjects = class_subjects.get(f"{selected_class_id}-{selected_division_id}", [])

        # Show students only if Show Students button was clicked
        if request.method == 'POST' and request.form.get('show_students') and selected_class_id and selected_division_id and request.form.get('subject'):
            subject_id = int(request.form.get('subject'))
            cur.execute("""
                SELECT st.id, u.name
                FROM students st
                JOIN users u ON st.user_id = u.id
                WHERE st.class_id = %s AND st.division_id = %s
                ORDER BY u.name
            """, (selected_class_id, selected_division_id))
            students = cur.fetchall()
        # Save attendance only if Submit Attendance button was clicked
        elif request.method == 'POST' and request.form.get('submit_attendance') and selected_class_id and selected_division_id and request.form.get('subject'):
            subject_id = int(request.form.get('subject'))
            date_data = form.date.data
            cur.execute("""
                SELECT st.id, u.name
                FROM students st
                JOIN users u ON st.user_id = u.id
                WHERE st.class_id = %s AND st.division_id = %s
                ORDER BY u.name
            """, (selected_class_id, selected_division_id))
            students = cur.fetchall()
            # Check if attendance already recorded
            cur.execute("SELECT COUNT(*) as count FROM attendance WHERE subject_id=%s AND date=%s", (subject_id, date_data))
            if cur.fetchone()['count'] > 0:
                flash('Attendance already recorded for this subject and date. Cannot re-record.', 'danger')
                return redirect(url_for('enter_attendance'))
            # Record attendance for each student
            for student in students:
                present = request.form.get(f'present_{student["id"]}') == 'on'
                cur.execute("""
                    INSERT INTO attendance (student_id, subject_id, status, date, recorded_by)
                    VALUES (%s, %s, %s, %s, %s)
                """, (student['id'], subject_id, 'present' if present else 'absent', date_data, session['user_id']))
            db.commit()
            flash('Attendance recorded successfully', 'success')
            return redirect(url_for('faculty_dashboard'))
    db.close()
    return render_template('enter_attendance.html', form=form, students=students,
        assigned_classes=assigned_classes, assigned_divisions=assigned_divisions,
        filtered_subjects=filtered_subjects, class_divisions=class_divisions, class_subjects=class_subjects,
        selected_class_id=selected_class_id, selected_division_id=selected_division_id)


@app.route('/faculty/enter_marks', methods=['GET', 'POST'])
@login_required('faculty')
def enter_marks():
    """Faculty route to enter marks for their assigned classes/subjects."""
    db = get_db()
    form = MarksForm()
    students = []
    
    with db.cursor() as cur:
        # Get subjects and associated class/division the faculty teaches (for form dropdown)
        cur.execute("""
            SELECT fa.subject_id as id, s.name, fa.class_id, fa.division_id
            FROM faculty_assignments fa 
            JOIN subjects s ON fa.subject_id=s.id 
            WHERE fa.faculty_user_id=%s
            ORDER BY s.name
        """, (session['user_id'],))
        assignments = cur.fetchall()
        
        # Populate subject dropdown choices
        form.subject.choices = [(a['id'], f"{a['name']} (C:{a['class_id']} D:{a['division_id']})") for a in assignments]
        
        if form.validate_on_submit():
            # If a subject is selected, fetch the list of students for that class/division
            subject_id = form.subject.data
            date_data = form.date.data

            # Find the class_id and division_id from the selected subject
            selected_assignment = next((a for a in assignments if a['id'] == int(subject_id)), None)

            if selected_assignment:
                class_id = selected_assignment['class_id']
                division_id = selected_assignment['division_id']

                # Get the relevant students
                cur.execute("""
                    SELECT st.id, u.name 
                    FROM students st 
                    JOIN users u ON st.user_id=u.id 
                    WHERE st.class_id=%s AND st.division_id=%s 
                    ORDER BY u.name
                """, (class_id, division_id))
                students = cur.fetchall()

                # Record marks for each student
                for student in students:
                    marks = request.form.get(f'marks_{student["id"]}')
                    if marks is not None and marks.strip() != '': # Only insert if marks are provided
                        try:
                            marks_float = float(marks)
                            # Check if marks already recorded for this subject, student, and date
                            cur.execute("SELECT COUNT(*) FROM marks WHERE student_id=%s AND subject_id=%s AND date=%s", (student['id'], subject_id, date_data))
                            if cur.fetchone()['COUNT(*)'] == 0:
                                cur.execute("""
                                    INSERT INTO marks (student_id, subject_id, marks, date, recorded_by) 
                                    VALUES (%s, %s, %s, %s, %s)
                                """, (student['id'], subject_id, marks_float, date_data, session['user_id']))
                            else:
                                # Optionally update existing marks instead of insertion
                                cur.execute("""
                                    UPDATE marks SET marks=%s 
                                    WHERE student_id=%s AND subject_id=%s AND date=%s
                                """, (marks_float, student['id'], subject_id, date_data))
                                
                        except ValueError:
                            flash(f'Invalid marks provided for student {student["name"]}.', 'warning')
                            db.rollback()
                            return redirect(url_for('enter_marks')) # Stop processing on error

                db.commit()
                flash('Marks recorded successfully', 'success')
                return redirect(url_for('faculty_dashboard'))
            else:
                 flash('Invalid subject assignment selected.', 'danger')

    db.close()
    return render_template('enter_marks.html', form=form, students=students)


@app.route('/faculty/defaulters')
@login_required('faculty')
def faculty_defaulters():
    """Faculty route to view defaulters for their assigned subjects/classes."""
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    threshold_arg = request.args.get('threshold', '75')
    class_id = request.args.get('class_id', type=int)
    division_id = request.args.get('division_id', type=int)
    try:
        threshold = float(threshold_arg) if threshold_arg.strip() else 75.0
    except ValueError:
        threshold = 75.0
    db = get_db()
    user_id = session['user_id']
    with db.cursor() as cur:
        # Get assigned classes/divisions for this faculty
        cur.execute("""
            SELECT fa.class_id, c.name as class_name, fa.division_id, d.name as division_name
            FROM faculty_assignments fa
            JOIN classes c ON fa.class_id = c.id
            JOIN divisions d ON fa.division_id = d.id
            WHERE fa.faculty_user_id = %s
            GROUP BY fa.class_id, fa.division_id
            ORDER BY c.name, d.name
        """, (user_id,))
        assignments = cur.fetchall()
        class_ids = sorted(set(a['class_id'] for a in assignments))
        division_ids = sorted(set(a['division_id'] for a in assignments))
        classes = [{'id': a['class_id'], 'name': a['class_name']} for a in assignments]
        divisions = [{'id': a['division_id'], 'name': a['division_name']} for a in assignments]
        # Remove duplicates
        seen_classes = set()
        unique_classes = []
        for c in classes:
            if c['id'] not in seen_classes:
                unique_classes.append(c)
                seen_classes.add(c['id'])
        classes = unique_classes
        seen_divisions = set()
        unique_divisions = []
        for d in divisions:
            if d['id'] not in seen_divisions:
                unique_divisions.append(d)
                seen_divisions.add(d['id'])
        divisions = unique_divisions
        # Defaulter query with class/division filter
        query = '''
SELECT st.id as student_id, u.name as student, s.name as subject,
ROUND(100*SUM(a.status='present')/COUNT(a.id),2) as percent,
COUNT(a.id) as total_classes
FROM attendance a
JOIN students st ON a.student_id=st.id
JOIN users u ON st.user_id=u.id
JOIN subjects s ON a.subject_id=s.id
WHERE DATE_FORMAT(a.date, '%%Y-%%m')=%s 
    AND a.subject_id IN (
            SELECT subject_id FROM faculty_assignments WHERE faculty_user_id=%s
    )
'''
        params = [month, user_id]
        if class_id:
            query += ' AND st.class_id=%s'
            params.append(class_id)
        if division_id:
            query += ' AND st.division_id=%s'
            params.append(division_id)
        query += ''' GROUP BY st.id, a.subject_id HAVING percent < %s ORDER BY percent DESC '''
        params.append(threshold)
        cur.execute(query, params)
        defaulters = cur.fetchall()
    db.close()
    return render_template('defaulters.html', defaulters=defaulters, month=month, threshold=threshold, classes=classes, divisions=divisions, selected_class_id=class_id, selected_division_id=division_id)

# Faculty: View Students with filter by class/division
@app.route('/faculty/students')
@login_required('faculty')
def faculty_students():
    class_id = request.args.get('class_id', type=int)
    division_id = request.args.get('division_id', type=int)
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT id, name FROM classes ORDER BY name")
        classes = cur.fetchall()
        # Filter divisions: if class selected, show only assigned divisions
        if class_id:
            cur.execute("""
                SELECT d.id, d.name FROM class_divisions cd
                JOIN divisions d ON cd.division_id = d.id
                WHERE cd.class_id = %s
                ORDER BY d.name
            """, (class_id,))
            divisions = cur.fetchall()
        else:
            cur.execute("SELECT id, name FROM divisions ORDER BY name")
            divisions = cur.fetchall()
        query = '''
            SELECT st.roll_no, st.name, st.email, st.phone, c.name as class_name, d.name as division_name
            FROM students st
            JOIN classes c ON st.class_id = c.id
            JOIN divisions d ON st.division_id = d.id
            WHERE 1=1
        '''
        params = []
        if class_id:
            query += " AND st.class_id=%s"
            params.append(class_id)
        if division_id:
            query += " AND st.division_id=%s"
            params.append(division_id)
        query += " ORDER BY st.roll_no"
        cur.execute(query, params)
        students = cur.fetchall()
    db.close()
    return render_template('faculty_students.html', students=students, classes=classes, divisions=divisions)


@app.route('/faculty/profile', methods=['GET', 'POST'])
@login_required('faculty')
def faculty_profile():
    """Faculty profile management route."""
    db = get_db()
    form = ProfileForm()
    
    with db.cursor() as cur:
        cur.execute("SELECT name, email FROM users WHERE id=%s", (session['user_id'],))
        user = cur.fetchone()
        
        if request.method == 'GET':
            form.name.data = user['name']
            form.email.data = user['email']
            
        if form.validate_on_submit():
            name = form.name.data or user['name']
            email = form.email.data or user['email']
            
            # Check for email change collision
            if email != user['email']:
                 cur.execute("SELECT id FROM users WHERE email=%s AND id!=%s", (email, session['user_id']))
                 if cur.fetchone():
                    flash('This email is already taken.', 'danger')
                    db.close()
                    return render_template('profile.html', form=form)

            try:
                if form.password.data:
                    password = generate_password_hash(form.password.data)
                    cur.execute("UPDATE users SET name=%s, email=%s, password=%s WHERE id=%s", (name, email, password, session['user_id']))
                else:
                    cur.execute("UPDATE users SET name=%s, email=%s WHERE id=%s", (name, email, session['user_id']))
                
                db.commit()
                flash('Profile updated successfully', 'success')
                return redirect(url_for('faculty_profile'))
            except pymysql.err.IntegrityError:
                db.rollback()
                flash('Failed to update profile (Email conflict).', 'danger')

    db.close()
    return render_template('profile.html', form=form)


# --- Student Routes ---

# --- Student/Faculty: View Published Results ---
@app.route('/view_results', methods=['GET'])
@login_required()
def view_results():
    user_role = session.get('role')
    user_id = session.get('user_id')
    db = get_db()
    exams = []
    students = []
    subjects = []
    marks = {}
    selected_exam_id = request.args.get('exam_id')
    selected_class_id = request.args.get('class_id')
    exam_classes = []
    show_class_select = False
    if user_role == 'student':
        # ...existing code for student...
        with db.cursor() as cur:
            cur.execute('SELECT class_id, id FROM students WHERE user_id=%s', (user_id,))
            srow = cur.fetchone()
            if srow:
                class_id = srow['class_id']
                student_id = srow['id']
                cur.execute('''SELECT e.id, e.name, e.year, e.month, c.name AS class_name FROM exams e JOIN classes c ON c.id=e.class_id WHERE e.class_id=%s AND e.published=1 ORDER BY e.year DESC, e.month DESC''', (class_id,))
                exams = cur.fetchall()
                if selected_exam_id:
                    cur.execute('SELECT * FROM exams WHERE id=%s AND published=1', (selected_exam_id,))
                    exam = cur.fetchone()
                    if exam:
                        cur.execute('SELECT id, name FROM subjects WHERE class_id=%s', (exam['class_id'],))
                        subjects = cur.fetchall()
                        cur.execute('SELECT id, name, roll_no FROM students WHERE class_id=%s ORDER BY roll_no', (exam['class_id'],))
                        students = cur.fetchall()
                        # Build marks dict only for subjects in this class/exam
                        subject_ids = set(subj['id'] for subj in subjects)
                        cur.execute('SELECT student_id, subject_id, marks, out_of FROM marks WHERE exam_id=%s', (selected_exam_id,))
                        for row in cur.fetchall():
                            if row['subject_id'] in subject_ids:
                                marks[(row['student_id'], row['subject_id'])] = {'marks': row['marks'], 'out_of': row['out_of']}
                        # Fill missing marks with zeroes for only valid subjects
                        for student in students:
                            for subj in subjects:
                                if (student['id'], subj['id']) not in marks:
                                    marks[(student['id'], subj['id'])] = {'marks': 0, 'out_of': 0}
    elif user_role == 'faculty':
        # Get all published exams for classes faculty is assigned to, latest first
        with db.cursor() as cur:
            cur.execute('''SELECT DISTINCT e.id, e.name, e.year, e.month FROM exams e JOIN faculty_assignments fa ON fa.class_id=e.class_id WHERE fa.faculty_user_id=%s AND e.published=1 ORDER BY e.year DESC, e.month DESC, e.id DESC''', (user_id,))
            exams = cur.fetchall()
        # If exam selected, get all classes for that exam
        if selected_exam_id:
            with db.cursor() as cur:
                cur.execute('SELECT class_id FROM exams WHERE id=%s', (selected_exam_id,))
                exam_row = cur.fetchone()
                if exam_row:
                    exam_class_id = exam_row['class_id']
                    # Get all classes for this exam (faculty may be assigned to multiple classes for this exam)
                    cur.execute('''SELECT DISTINCT c.id, c.name FROM classes c JOIN faculty_assignments fa ON fa.class_id=c.id WHERE fa.faculty_user_id=%s AND c.id=%s''', (user_id, exam_class_id))
                    exam_classes = cur.fetchall()
                    if len(exam_classes) == 1:
                        selected_class_id = exam_classes[0]['id']
                    else:
                        show_class_select = True
        # If class selected, show results for that class
        if selected_exam_id and selected_class_id:
            with db.cursor() as cur:
                cur.execute('SELECT id, name FROM subjects WHERE class_id=%s', (selected_class_id,))
                subjects = cur.fetchall()
                cur.execute('SELECT id, name, roll_no FROM students WHERE class_id=%s ORDER BY roll_no', (selected_class_id,))
                students = cur.fetchall()
                subject_ids = set(subj['id'] for subj in subjects)
                cur.execute('SELECT student_id, subject_id, marks, out_of FROM marks WHERE exam_id=%s', (selected_exam_id,))
                for row in cur.fetchall():
                    if row['subject_id'] in subject_ids:
                        marks[(row['student_id'], row['subject_id'])] = {'marks': row['marks'], 'out_of': row['out_of']}
                # Fill missing marks with zeroes for only valid subjects
                for student in students:
                    for subj in subjects:
                        if (student['id'], subj['id']) not in marks:
                            marks[(student['id'], subj['id'])] = {'marks': 0, 'out_of': 0}
    db.close()
    return render_template('view_results.html', exams=exams, students=students, subjects=subjects, marks=marks, selected_exam_id=selected_exam_id, selected_class_id=selected_class_id, exam_classes=exam_classes, show_class_select=show_class_select)

@app.route('/student')
@login_required('student')
def student_dashboard():
    """Student dashboard showing marks and attendance."""
    db = get_db()
    
    # Get student's internal ID from user_id
    student_id = None
    class_id = None
    with db.cursor() as cur:
        cur.execute("SELECT id, class_id FROM students WHERE user_id=%s", (session['user_id'],))
        student_row = cur.fetchone()
        if student_row:
            student_id = student_row['id']
            class_id = student_row['class_id']
    
    marks = []
    attendance = []
    defaulter = False
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    
    if student_id:
        with db.cursor() as cur:
            # --- MARKS ---
            # Get subjects where the student has recorded marks
            cur.execute("""
                SELECT DISTINCT s.id, s.name FROM subjects s 
                JOIN marks m ON s.id=m.subject_id 
                WHERE m.student_id=%s
                ORDER BY s.name
            """, (student_id,))
            subjects = cur.fetchall()

            for subj in subjects:
                # Calculate average mark
                cur.execute("SELECT AVG(marks) as average FROM marks WHERE student_id=%s AND subject_id=%s", (student_id, subj['id']))
                avg = cur.fetchone()['average'] or 0
                
                # Get mark history
                cur.execute("SELECT marks, DATE_FORMAT(date, '%%Y-%%m-%%d') as date FROM marks WHERE student_id=%s AND subject_id=%s ORDER BY date DESC", (student_id, subj['id']))
                history = cur.fetchall()
                
                marks.append({'name': subj['name'], 'average': round(avg, 2), 'history': history})

            # --- ATTENDANCE ---
            # Get subjects where the student has recorded attendance
            cur.execute("""
                SELECT DISTINCT s.id, s.name FROM subjects s 
                JOIN attendance a ON s.id=a.subject_id 
                WHERE a.student_id=%s
                ORDER BY s.name
            """, (student_id,))
            subjects_att = cur.fetchall()

            for subj in subjects_att:
                # Calculate attendance for the filtered month
                cur.execute("""
                    SELECT SUM(status='present') as presents, COUNT(id) as total 
                    FROM attendance 
                    WHERE student_id=%s AND subject_id=%s AND DATE_FORMAT(date, '%%Y-%%m')=%s
                """, (student_id, subj['id'], month))
                att = cur.fetchone()
                total_classes = att['total']
                percent = round(100 * att['presents'] / total_classes, 2) if total_classes else 0
                attendance.append({'name': subj['name'], 'percent': percent, 'total': total_classes})
                if percent > 0 and percent < 75: # Only warn if there were classes recorded
                    defaulter = True
    
    # Get student name for navbar
    student_name = None
    with db.cursor() as cur:
        cur.execute("SELECT name FROM users WHERE id=%s", (session['user_id'],))
        row = cur.fetchone()
        if row:
            student_name = row['name']
    # Check today's attendance for each subject
    from datetime import date
    today_str = date.today().strftime('%Y-%m-%d')
    todays_attendance = []
    if student_id:
        with db.cursor() as cur:
            cur.execute("SELECT s.name, a.status FROM subjects s LEFT JOIN attendance a ON s.id=a.subject_id AND a.student_id=%s AND a.date=%s WHERE s.class_id=%s", (student_id, today_str, class_id))
            for row in cur.fetchall():
                todays_attendance.append({'subject': row['name'], 'status': row['status']})
    db.close()
    return render_template('student_dashboard.html', marks=marks, attendance=attendance, month=month, defaulter=defaulter, student_name=student_name, todays_attendance=todays_attendance)
# --- Student Attendance Register Route ---
@app.route('/student/attendance_register')
@login_required('student')
def student_attendance_register():
    db = get_db()
    student_id = None
    with db.cursor() as cur:
        cur.execute("SELECT id, name FROM students WHERE user_id=%s", (session['user_id'],))
        student_row = cur.fetchone()
        if student_row:
            student_id = student_row['id']
            student_name = student_row['name']
        else:
            student_name = None
    today = datetime.today().strftime('%Y-%m-%d')
    attendance_today = None
    if student_id:
        with db.cursor() as cur:
            cur.execute("SELECT status FROM attendance WHERE student_id=%s AND date=%s", (student_id, today))
            row = cur.fetchone()
            if row:
                attendance_today = row['status']
    db.close()
    return render_template('student_attendance_register.html', today=today, attendance_today=attendance_today, student_name=student_name)

@app.route('/student/profile', methods=['GET', 'POST'])
@login_required('student')
def student_profile():
    """Student profile management route."""
    db = get_db()
    form = ProfileForm()
    
    with db.cursor() as cur:
        cur.execute("SELECT name, email FROM users WHERE id=%s", (session['user_id'],))
        user = cur.fetchone()
        
        if request.method == 'GET':
            form.name.data = user['name']
            form.email.data = user['email']
            
        if form.validate_on_submit():
            name = form.name.data or user['name']
            email = form.email.data or user['email']
            
            # Check for email change collision
            if email != user['email']:
                 cur.execute("SELECT id FROM users WHERE email=%s AND id!=%s", (email, session['user_id']))
                 if cur.fetchone():
                    flash('This email is already taken.', 'danger')
                    db.close()
                    return render_template('profile.html', form=form)

            try:
                if form.password.data:
                    password = generate_password_hash(form.password.data)
                    cur.execute("UPDATE users SET name=%s, email=%s, password=%s WHERE id=%s", (name, email, password, session['user_id']))
                else:
                    cur.execute("UPDATE users SET name=%s, email=%s WHERE id=%s", (name, email, session['user_id']))
                
                db.commit()
                flash('Profile updated successfully', 'success')
                return redirect(url_for('faculty_profile'))
            except pymysql.err.IntegrityError:
                db.rollback()
                flash('Failed to update profile (Email conflict).', 'danger')

    db.close()
    return render_template('profile.html', form=form)



if __name__ == '__main__':
    # Call this function once at startup to ensure schema is up to date
    create_exams_table()
    app.run(debug=True)
''
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
