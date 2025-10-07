import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import '../styles/Navigation.css'

const Navigation = () => {
  const location = useLocation()

  const handleLogout = () => {
    localStorage.removeItem('token')
    window.location.href = '/login'
  }

  return (
    <nav className="navbar navbar-expand-lg navbar-dark bg-primary">
      <div className="container-fluid">
        <Link className="navbar-brand" to="/">
          <i className="bi bi-mortarboard-fill me-2"></i>
          Exam Management System
        </Link>

        <button
          className="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#navbarNav"
        >
          <span className="navbar-toggler-icon"></span>
        </button>

        <div className="collapse navbar-collapse" id="navbarNav">
          <ul className="navbar-nav me-auto">
            <li className="nav-item">
              <Link
                className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}
                to="/"
              >
                <i className="bi bi-speedometer2 me-1"></i>
                Dashboard
              </Link>
            </li>
            <li className="nav-item dropdown">
              <a
                className="nav-link dropdown-toggle"
                href="#"
                role="button"
                data-bs-toggle="dropdown"
              >
                <i className="bi bi-upload me-1"></i>
                Upload Data
              </a>
              <ul className="dropdown-menu">
                <li>
                  <Link
                    className={`dropdown-item ${location.pathname === '/upload-students' ? 'active' : ''}`}
                    to="/upload-students"
                  >
                    <i className="bi bi-people me-2"></i>Upload Students
                  </Link>
                </li>
                <li>
                  <Link
                    className={`dropdown-item ${location.pathname === '/upload-staff' ? 'active' : ''}`}
                    to="/upload-staff"
                  >
                    <i className="bi bi-person-badge me-2"></i>Upload Staff
                  </Link>
                </li>
                <li>
                  <Link
                    className={`dropdown-item ${location.pathname === '/upload-halls' ? 'active' : ''}`}
                    to="/upload-halls"
                  >
                    <i className="bi bi-building me-2"></i>Upload Halls
                  </Link>
                </li>
              </ul>
            </li>
            <li className="nav-item">
              <Link
                className={`nav-link ${location.pathname === '/seating-plan' ? 'active' : ''}`}
                to="/seating-plan"
              >
                <i className="bi bi-diagram-3 me-1"></i>
                Seating Plan
              </Link>
            </li>
            <li className="nav-item">
              <Link
                className={`nav-link ${location.pathname === '/hall-tickets' ? 'active' : ''}`}
                to="/hall-tickets"
              >
                <i className="bi bi-card-heading me-1"></i>
                Hall Tickets
              </Link>
            </li>
            <li className="nav-item">
              <Link
                className={`nav-link ${location.pathname === '/reports' ? 'active' : ''}`}
                to="/reports"
              >
                <i className="bi bi-graph-up me-1"></i>
                Reports
              </Link>
            </li>
          </ul>

          <ul className="navbar-nav">
            <li className="nav-item">
              <button className="btn btn-outline-light btn-sm" onClick={handleLogout}>
                <i className="bi bi-box-arrow-right me-1"></i>
                Logout
              </button>
            </li>
          </ul>
        </div>
      </div>
    </nav>
  )
}

export default Navigation
