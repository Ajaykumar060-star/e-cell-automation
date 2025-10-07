# Exam Management System — MERN Backend

Node.js + Express + MongoDB backend for the Exam Management System, migrated from Flask.

## Requirements
- Node.js 18+
- MongoDB 6+

## Installation
```
cd server
npm install
cp .env.example .env
# edit .env if needed
npm run dev
```
Server runs on: http://localhost:5000

## Environment Variables
- PORT=5000
- MONGO_URI=mongodb://localhost:27017/exam_management
- CLIENT_ORIGIN=http://localhost:3000

## Folder Structure
```
server/
  server.js
  .env.example
  src/
    config/db.js
    middleware/upload.js
    models/
      Counter.js
      Student.js
      Staff.js
      Hall.js
      Exam.js
      Attendance.js
      SeatingAllocation.js
    controllers/
      studentsController.js
      staffController.js
      hallsController.js
      examsController.js
      attendanceController.js
      uploadController.js
      seatingController.js
      hallTicketsController.js
      statsController.js
    routes/
      students.js
      staff.js
      halls.js
      exams.js
      attendance.js
      upload.js
      seating.js
      hallTickets.js
      stats.js
    utils/
      parse.js
      normalize.js
      allocate.js
      excel.js
      sequence.js
  outputs/  # generated excel files
  uploads/  # temporary uploads
```

## API Overview

- Students (id is numeric sequence like Flask Mongo engine)
  - GET /api/students
  - GET /api/students/:id
  - POST /api/students
  - PUT /api/students/:id
  - DELETE /api/students/:id

- Staff
  - GET /api/staff
  - GET /api/staff/:id
  - POST /api/staff
  - PUT /api/staff/:id
  - DELETE /api/staff/:id

- Halls
  - GET /api/halls
  - POST /api/halls
  - GET /api/halls/:id
  - PUT /api/halls/:id
  - DELETE /api/halls/:id

- Exams
  - GET /api/exams
  - GET /api/exams/:id
  - POST /api/exams
  - PUT /api/exams/:id
  - DELETE /api/exams/:id

- Attendance
  - GET /api/attendances
  - POST /api/attendances
  - GET /api/attendances/:id
  - PUT /api/attendances/:id
  - DELETE /api/attendances/:id

- Uploads (CSV/Excel via `file` field)
  - POST /api/upload/students
  - POST /api/upload/staff
  - POST /api/upload/halls
  - POST /api/upload/timetable  (alias also at /api/v2/upload/timetable)
    - body: `capacity` (optional, default 30)
    - returns preview, summary, and `download_url` to excel in `/outputs`

- Seating
  - GET /api/seating              (query: date, sess, subject, page, limit)
  - GET /api/seating/summary      (query: date, sess)
  - DELETE /api/seating           (clear all allocations)
  - GET /api/seating/latest-output

- Hall Tickets
  - GET /api/hall-tickets/student/:reg_no
  - GET /api/hall-tickets/subject/:sub_code
  - GET /api/hall-tickets/:date/:sess/hall/:hall_no

- Stats
  - GET /api/stats/counts
  - GET /api/stats/subjects       (query: date, sess)

- Health
  - GET /api/health

## Notes
- CORS is enabled for `CLIENT_ORIGIN`.
- File uploads handled with Multer; temporary files are removed after processing.
- Seating allocation and excel generation mirror the existing Flask logic.

## Next
- Build React client in `/client` and wire to these APIs.
