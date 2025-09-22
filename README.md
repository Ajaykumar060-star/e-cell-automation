# Exam Hall Management System

This is a comprehensive exam hall management system for colleges, built with Python Flask and MySQL.

## Features

1. **Admin Authentication**
   - Secure login system for administrators
   - Default credentials: admin / admin123

2. **Data Management**
   - Manage students, staff, and halls
   - Manual entry through web forms
   - Bulk import via CSV/Excel files

3. **User-Friendly Interface**
   - Professional, responsive design
   - Intuitive navigation
   - Clear data visualization

## Installation

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Set up your MySQL database and update the `.env` file with your database credentials.

3. Run the application:
   ```
   python app.py
   ```

4. Access the application at `http://localhost:5000`

## Usage

### Admin Login
- Navigate to `http://localhost:5000/login`
- Use default credentials: admin / admin123
- Change the password after first login for security

### Managing Data

#### Students
- Add individual students manually using the "Add Student" button
- Upload CSV/Excel files using the "Upload CSV/Excel" button
- Required columns for file upload: name, email, phone, department, year

#### Staff
- Add individual staff members manually using the "Add Staff" button
- Upload CSV/Excel files using the "Upload CSV/Excel" button
- Required columns for file upload: name, email, phone, department, role

#### Halls
- Add individual halls manually using the "Add Hall" button
- Upload CSV/Excel files using the "Upload CSV/Excel" button
- Required columns for file upload: name, capacity, location, facilities

### File Format Requirements

#### Students CSV/Excel Format
```
name,email,phone,department,year
John Doe,john@example.com,1234567890,Computer Science,3rd
Jane Smith,jane@example.com,0987654321,Electronics,2nd
```

#### Staff CSV/Excel Format
```
name,email,phone,department,role
Dr. Alan Turing,alan@example.com,5566778899,Computer Science,Professor
Dr. Marie Curie,marie@example.com,9988776655,Physics,Professor
```

#### Halls CSV/Excel Format
```
name,capacity,location,facilities
Main Hall A,100,First Floor,"AC, Projector, Whiteboard"
Lab Hall C,60,Second Floor,"AC, Computers, Projector"
```

## Security Notes

- Change the default admin password immediately after first login
- Update the SECRET_KEY in the `.env` file for production use
- Ensure your MySQL database is secured with a strong password

## Technologies Used

- Python Flask (Backend)
- MySQL (Database)
- HTML/CSS/JavaScript with Bootstrap (Frontend)
- Pandas (Data processing)
- OpenPyXL (Excel file handling)
