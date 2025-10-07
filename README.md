# Exam Management System - MERN Stack

A modern, full-stack web application for managing exam seating arrangements, hall tickets, and student/staff data. Built with React (frontend), Node.js/Express (backend), and MongoDB (database).

## 🚀 Features

- **Student Management**: Upload and manage student data via CSV files
- **Staff Management**: Upload and manage staff data via CSV files
- **Hall Management**: Upload and manage exam hall data via CSV files
- **Seating Plan Generation**: Automated seating arrangement generation
- **Hall Ticket Generation**: Generate hall tickets for exams
- **Reports & Analytics**: Comprehensive reporting dashboard
- **Responsive Design**: Works seamlessly on desktop and mobile devices

## 🏗️ Architecture

### Frontend (React)
- **Framework**: React 18 with Vite
- **Routing**: React Router DOM v6
- **HTTP Client**: Axios
- **Styling**: Plain CSS with Bootstrap Icons
- **State Management**: React Hooks

### Backend (Node.js/Express)
- **Runtime**: Node.js with ES6 modules
- **Framework**: Express.js
- **Database**: MongoDB with Mongoose ODM
- **File Upload**: Multer
- **Security**: Helmet, CORS enabled

## 📁 Project Structure

```
exam-management-system/
├── client/                 # React frontend
│   ├── public/            # Static assets
│   ├── src/
│   │   ├── components/    # Reusable React components
│   │   │   ├── Navigation.jsx
│   │   │   └── ProtectedRoute.jsx
│   │   ├── pages/         # Page components
│   │   │   ├── Login.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── UploadStudents.jsx
│   │   │   ├── UploadStaff.jsx
│   │   │   ├── UploadHalls.jsx
│   │   │   ├── SeatingPlan.jsx
│   │   │   ├── HallTickets.jsx
│   │   │   └── Reports.jsx
│   │   ├── services/      # API services
│   │   │   └── api.js
│   │   ├── styles/        # CSS files
│   │   └── App.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── server/                # Node.js backend
│   ├── src/
│   │   ├── config/       # Database configuration
│   │   ├── controllers/  # Route controllers
│   │   ├── middleware/   # Custom middleware
│   │   ├── models/       # Mongoose models
│   │   ├── routes/       # API routes
│   │   └── utils/        # Utility functions
│   ├── server.js         # Main server file
│   ├── package.json
│   └── README.md
├── sample_*.csv          # Sample data files
└── README.md
```

## 🛠️ Installation & Setup

### Prerequisites
- Node.js (v16 or higher)
- MongoDB (local installation or MongoDB Atlas)
- Git

### Backend Setup

1. **Navigate to server directory:**
   ```bash
   cd server
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Environment Configuration:**
   ```bash
   cp .env.example .env
   ```

   Update the `.env` file with your MongoDB connection string:
   ```env
   MONGODB_URI=mongodb://localhost:27017/exam-management
   PORT=5000
   CLIENT_ORIGIN=http://localhost:3000
   JWT_SECRET=your-jwt-secret-key
   ```

4. **Start MongoDB** (if running locally)

5. **Start the server:**
   ```bash
   npm run dev
   ```

   The server will start on `http://localhost:5000`

### Frontend Setup

1. **Navigate to client directory:**
   ```bash
   cd client
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Environment Configuration:**
   Create a `.env` file in the client directory:
   ```env
   VITE_API_URL=http://localhost:5000/api
   ```

4. **Start the development server:**
   ```bash
   npm run dev
   ```

   The frontend will start on `http://localhost:3000`

## 🔧 Usage

1. **Access the application** at `http://localhost:3000`

2. **Login** with default credentials:
   - Username: `admin`
   - Password: `admin123`

3. **Upload Data:**
   - Use the sample CSV files in the root directory as templates
   - Navigate to "Upload Data" section to upload students, staff, and halls

4. **Generate Seating Plans:**
   - Go to "Seating Plan" section
   - Select an exam and generate seating arrangements

5. **Generate Hall Tickets:**
   - Go to "Hall Tickets" section
   - Select an exam to generate hall tickets for all students

6. **View Reports:**
   - Check the "Reports" section for comprehensive analytics

## 📊 API Endpoints

### Authentication
- `POST /api/auth/login` - User login

### Students
- `GET /api/students` - Get all students
- `POST /api/students` - Create student
- `GET /api/students/stats` - Get student statistics
- `GET /api/students/report` - Get student report

### Staff
- `GET /api/staff` - Get all staff
- `POST /api/staff` - Create staff
- `GET /api/staff/stats` - Get staff statistics
- `GET /api/staff/report` - Get staff report

### Halls
- `GET /api/halls` - Get all halls
- `POST /api/halls` - Create hall
- `GET /api/halls/stats` - Get hall statistics
- `GET /api/halls/report` - Get hall report

### Exams
- `GET /api/exams` - Get all exams
- `POST /api/exams` - Create exam
- `GET /api/exams/report` - Get exam report

### File Upload
- `POST /api/upload/students` - Upload students CSV
- `POST /api/upload/staff` - Upload staff CSV
- `POST /api/upload/halls` - Upload halls CSV

### Seating
- `POST /api/seating/generate/:examId` - Generate seating plan

### Hall Tickets
- `GET /api/hall-tickets/students/:examId` - Get students for exam
- `POST /api/hall-tickets/generate/:examId` - Generate hall tickets

## 🔒 Security Features

- CORS enabled with configurable origins
- Helmet.js for security headers
- JWT-based authentication
- Input validation and sanitization
- File upload restrictions

## 🚀 Deployment

### Backend Deployment
```bash
cd server
npm run build
npm start
```

### Frontend Deployment
```bash
cd client
npm run build
```

Serve the `dist` folder with any static file server.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support, email support@example.com or create an issue in the repository.

---

Built with ❤️ using MERN Stack

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
"# e-cell-automation" 
"# e-cell-automation" 
"# e-cell-automation" 
