CREATE DATABASE IF NOT EXISTS exam_management;
USE exam_management;

CREATE TABLE students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(15) NOT NULL,
    department VARCHAR(50) NOT NULL,
    year VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE staff (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(15) NOT NULL,
    department VARCHAR(50) NOT NULL,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE halls (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    capacity INT NOT NULL,
    location VARCHAR(100) NOT NULL,
    facilities TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE exams (
    id INT AUTO_INCREMENT PRIMARY KEY,
    subject VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    time TIME NOT NULL,
    duration INT NOT NULL,
    hall_id INT NOT NULL,
    staff_id INT NOT NULL,
    department VARCHAR(50) NOT NULL,
    year VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hall_id) REFERENCES halls(id),
    FOREIGN KEY (staff_id) REFERENCES staff(id)
);

CREATE TABLE attendances (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    exam_id INT NOT NULL,
    status VARCHAR(20) NOT NULL,
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (exam_id) REFERENCES exams(id)
);

ALTER TABLE exam ADD COLUMN status VARCHAR(20) DEFAULT 'upcoming';
ALTER TABLE hall ADD COLUMN room_number VARCHAR(20);



-- Insert some default halls
INSERT INTO halls (name, capacity, location, facilities) VALUES
('Main Hall A', 100, 'First Floor', 'AC, Projector, Whiteboard'),
('Main Hall B', 80, 'First Floor', 'AC, Projector'),
('Lab Hall C', 60, 'Second Floor', 'AC, Computers, Projector'),
('Auditorium', 200, 'Ground Floor', 'AC, Projector, Sound System'),
('Seminar Hall', 50, 'Third Floor', 'AC, Whiteboard');

-- Sample data for testing
-- Sample Students
INSERT INTO students (name, email, phone, department, year) VALUES
('John Doe', 'john.doe@example.com', '1234567890', 'Computer Science', '3rd'),
('Jane Smith', 'jane.smith@example.com', '0987654321', 'Electronics', '2nd'),
('Robert Johnson', 'robert.j@example.com', '1122334455', 'Mechanical', '4th');

-- Sample Staff
INSERT INTO staff (name, email, phone, department, role) VALUES
('Dr. Alan Turing', 'alan.turing@example.com', '5566778899', 'Computer Science', 'Professor'),
('Dr. Marie Curie', 'marie.curie@example.com', '9988776655', 'Physics', 'Professor'),
('Prof. Albert Einstein', 'albert.einstein@example.com', '4433221100', 'Mathematics', 'Professor');

-- Sample Exams
INSERT INTO exams (subject, date, time, duration, hall_id, staff_id, department, year) VALUES
('Data Structures', '2023-12-15', '10:00:00', 180, 1, 1, 'Computer Science', '3rd'),
('Digital Electronics', '2023-12-16', '14:00:00', 120, 2, 2, 'Electronics', '2nd');

-- Sample Attendance
INSERT INTO attendances (student_id, exam_id, status, remarks) VALUES
(1, 1, 'Present', 'Good performance'),
(2, 2, 'Absent', 'Medical leave');