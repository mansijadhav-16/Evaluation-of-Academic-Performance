# 📚 Evaluation of Academic Performance

A web-based academic management system built with **Flask** and **MySQL** that enables institutions to track student attendance, manage exam results, and evaluate academic performance — all from a single platform.

## 🌟 Features

### 👨‍💼 Admin
- Dashboard with system overview (total students, faculty, subjects)
- Manage classes, divisions, and subjects
- Add and edit faculty with subject/class/division assignments
- Create and manage exams
- Review and publish exam results
- View attendance defaulters across the institution

### 👩‍🏫 Faculty
- Dashboard showing assigned subjects, classes, and divisions
- Record and manage student attendance (subject-wise, date-wise)
- Enter and update exam marks for assigned students
- View attendance register and defaulter list
- Manage personal profile

### 🎓 Student
- Dashboard with attendance percentage and latest exam results
- View today's attendance status per subject
- Filter attendance by month
- View published exam marks
- Defaulter warning when attendance drops below 75%
- Manage personal profile

### 🔐 Authentication
- Role-based login (Admin / Faculty / Student)
- Forgot password with OTP via email
- Secure password hashing using Werkzeug

---

## 🛠️ Tech Stack

| Layer       | Technology              |
|-------------|-------------------------|
| Backend     | Python, Flask           |
| Frontend    | HTML, CSS, JavaScript, Bootstrap |
| Database    | MySQL (via PyMySQL)     |
| Forms       | Flask-WTF, WTForms      |
| Auth        | Werkzeug Security       |
| Email (OTP) | smtplib (Gmail SMTP)    |

---

## 📁 Project Structure

```
student attand/
│
├── app.py               # Main Flask application & all routes
├── config.py            # App configuration (DB, email, secret key)
├── db_init.sql          # MySQL database schema
├── requirements.txt     # Python dependencies
│
├── static/
│   ├── css/
│   │   └── style.css    # Custom styles
│   ├── js/
│   │   └── main.js      # Frontend JavaScript
│   └── images/          # Static images
│
└── templates/
    ├── base.html                     # Base layout template
    ├── home.html                     # Landing page
    ├── login.html                    # Login page
    ├── forgot_password.html          # OTP-based password reset
    ├── profile.html                  # Shared profile page
    │
    ├── admin_dashboard.html          # Admin overview
    ├── admin_classes.html            # Manage classes & divisions
    ├── admin_divisions.html          # Manage divisions
    ├── admin_class_subjects.html     # Manage subjects per class
    ├── admin_faculties.html          # View all faculty
    ├── add_faculty.html              # Add new faculty
    ├── edit_faculty.html             # Edit faculty assignments
    ├── admin_students.html           # View students (filtered)
    ├── admin_exams.html              # Create/manage exams
    ├── admin_review_results.html     # Review & publish results
    │
    ├── faculty_dashboard.html        # Faculty overview
    ├── faculty_students.html         # View assigned students
    ├── faculty_exam_marks.html       # Enter exam marks
    ├── enter_attendance.html         # Record attendance
    ├── enter_marks.html              # Enter marks (old flow)
    ├── attendance_register.html      # View attendance register
    ├── defaulters.html               # Attendance defaulters list
    │
    ├── student_dashboard.html        # Student overview
    ├── student_attendance_register.html  # Student's attendance view
    ├── view_results.html             # View published exam results
    └── add_student.html              # Add new student
```

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.8+
- MySQL Server
- pip

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up the Database

Open MySQL and run the provided SQL script:

```bash
mysql -u root -p < db_init.sql
```

### 4. Configure the App

Edit `config.py` with your own credentials:

```python
class Config:
    SECRET_KEY = 'your-secret-key'
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'your-mysql-password'
    MYSQL_DB = 'academic_performance'
    EMAIL_USER = 'your-email@gmail.com'
    EMAIL_PASS = 'your-app-password'   # Gmail App Password
```

> ⚠️ **Important:** Never commit real credentials to GitHub. Use environment variables or a `.env` file.

### 5. Run the Application

```bash
python app.py
```

Visit `http://127.0.0.1:5000` in your browser.

---

## 🗄️ Database Schema (Overview)

| Table                | Description                                      |
|----------------------|--------------------------------------------------|
| `users`              | All users (admin, faculty, student) with roles   |
| `students`           | Student details linked to a user account         |
| `classes`            | Academic classes (e.g., Class 10, FY B.Sc.)      |
| `divisions`          | Divisions/sections (e.g., A, B, C)               |
| `class_divisions`    | Maps divisions to classes                        |
| `subjects`           | Subjects linked to a class                       |
| `faculty_assignments`| Maps faculty to class/division/subject           |
| `attendance`         | Daily attendance records per student/subject     |
| `marks`              | Exam-wise marks per student/subject              |
| `exams`              | Exam records with publish status                 |

---

## 🔑 Default Login Roles

| Role    | How to Create                                      |
|---------|----------------------------------------------------|
| Admin   | Insert directly into the `users` table with `role='admin'` |
| Faculty | Created via Admin dashboard                        |
| Student | Created by Faculty; default password = roll number |

---

## 📧 Email / OTP Setup (Gmail)

To enable the forgot password feature:

1. Enable **2-Step Verification** on your Gmail account
2. Generate an **App Password** from Google Account Settings
3. Add the email and app password to `config.py`

---

## 📌 Key Routes

| Route | Role | Description |
|-------|------|-------------|
| `/` | All | Home page |
| `/login` | All | Login |
| `/admin` | Admin | Admin dashboard |
| `/admin/faculties` | Admin | Manage faculty |
| `/admin/exams` | Admin | Manage exams |
| `/admin/review_results` | Admin | Publish results |
| `/faculty` | Faculty | Faculty dashboard |
| `/faculty/enter_attendance` | Faculty | Record attendance |
| `/faculty/exam_marks` | Faculty | Enter exam marks |
| `/faculty/defaulters` | Faculty | View defaulters |
| `/student` | Student | Student dashboard |
| `/view_results` | Student/Faculty | View published results |
| `/forgot_password` | All | OTP-based password reset |

---

## 🚀 Future Improvements

- [ ] Export attendance reports to PDF / Excel
- [ ] Email notifications to defaulter students
- [ ] Charts and analytics for performance trends
- [ ] REST API for mobile app integration
- [ ] Dark mode support


## 👨‍💻 Author
Mansi Jadhav  
GitHub:(https://github.com/mansijadhav-16)
