-- Database: academic_performance
CREATE DATABASE IF NOT EXISTS academic_performance;
USE academic_performance;

-- Classes table
CREATE TABLE IF NOT EXISTS classes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE
);

-- Divisions table
CREATE TABLE IF NOT EXISTS divisions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(20) NOT NULL UNIQUE
);

-- Mapping table: which divisions belong to which class
CREATE TABLE IF NOT EXISTS class_divisions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    class_id INT,
    division_id INT,
    UNIQUE(class_id, division_id),
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (division_id) REFERENCES divisions(id) ON DELETE CASCADE
);

-- Users table (admin, faculty, student)
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(150),
    email VARCHAR(150) UNIQUE,
    password VARCHAR(255),
    role ENUM('admin','faculty','student'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Subjects table (linked to class)
CREATE TABLE IF NOT EXISTS subjects (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(150),
    class_id INT,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
);

-- Faculty assignments: which faculty teaches which subject in which class/division
CREATE TABLE IF NOT EXISTS faculty_assignments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    faculty_user_id INT,
    subject_id INT,
    class_id INT,
    division_id INT,
    UNIQUE(faculty_user_id, subject_id, class_id, division_id),
    FOREIGN KEY (faculty_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (division_id) REFERENCES divisions(id) ON DELETE CASCADE
);


-- Students table (latest structure: user_id, roll_no, name, email, phone, class_id, division_id)
CREATE TABLE IF NOT EXISTS students (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    roll_no VARCHAR(50),
    name VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20),
    class_id INT,
    division_id INT,
    UNIQUE (roll_no, class_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (division_id) REFERENCES divisions(id) ON DELETE CASCADE
);
-- Insert default admin user
INSERT INTO users (name, email, password, role) VALUES (
    'Admin',
    'admin@example.com',
    'scrypt:32768:8:1$c3e5BJRPVnWLgulS$f17dffb64bc99df9a99562ca727616cee594b89c590d89a3dc5c06c192c4ff7939d294a40f8e17db2c789ce3637df68e6ee025b3a27c3fc16045e3fcde1f172d',
    'admin'
);

-- Attendance table
CREATE TABLE IF NOT EXISTS attendance (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT,
    subject_id INT,
    status ENUM('present','absent'),
    date DATE,
    recorded_by INT,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    FOREIGN KEY (recorded_by) REFERENCES users(id) ON DELETE CASCADE
);

-- Exams table (NEW)
CREATE TABLE IF NOT EXISTS exams (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    year INT NOT NULL,
    month INT NOT NULL,
    class_id INT NOT NULL,
    published BOOLEAN DEFAULT 0,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
);

-- Marks table (UPDATED for exam system)
CREATE TABLE IF NOT EXISTS marks (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT,
    subject_id INT,
    exam_id INT,
    marks FLOAT,
    out_of INT DEFAULT 100,
    recorded_by INT,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE,
    FOREIGN KEY (recorded_by) REFERENCES users(id) ON DELETE CASCADE
);
