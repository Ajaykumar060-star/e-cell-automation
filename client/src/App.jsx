import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import './styles/index.css'

// Pages
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import UploadStudents from './pages/UploadStudents'
import UploadStaff from './pages/UploadStaff'
import UploadHalls from './pages/UploadHalls'
import SeatingPlan from './pages/SeatingPlan'
import HallTickets from './pages/HallTickets'
import Reports from './pages/Reports'

// Components
import Navigation from './components/Navigation'
import ProtectedRoute from './components/ProtectedRoute'

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={
            <ProtectedRoute>
              <Navigation />
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/upload-students" element={<UploadStudents />} />
                <Route path="/upload-staff" element={<UploadStaff />} />
                <Route path="/upload-halls" element={<UploadHalls />} />
                <Route path="/seating-plan" element={<SeatingPlan />} />
                <Route path="/hall-tickets" element={<HallTickets />} />
                <Route path="/reports" element={<Reports />} />
              </Routes>
            </ProtectedRoute>
          } />
        </Routes>
      </div>
    </Router>
  )
}

export default App
