import React, { useState, useEffect } from 'react'
import api from '../services/api'
import '../styles/Dashboard.css'

const Dashboard = () => {
  const [stats, setStats] = useState({
    totalStudents: 0,
    totalStaff: 0,
    totalHalls: 0,
    upcomingExams: 0
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const [studentsRes, staffRes, hallsRes, examsRes] = await Promise.all([
        api.get('/students/stats'),
        api.get('/staff/stats'),
        api.get('/halls/stats'),
        api.get('/exams/stats')
      ])

      setStats({
        totalStudents: studentsRes.data.total || 0,
        totalStaff: staffRes.data.total || 0,
        totalHalls: hallsRes.data.total || 0,
        upcomingExams: examsRes.data.upcoming || 0
      })
    } catch (error) {
      console.error('Error fetching stats:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleQuickAction = (action) => {
    switch (action) {
      case 'students':
        window.location.href = '/upload-students'
        break
      case 'staff':
        window.location.href = '/upload-staff'
        break
      case 'halls':
        window.location.href = '/upload-halls'
        break
      default:
        break
    }
  }

  if (loading) {
    return <div className="container-fluid p-4">Loading...</div>
  }

  return (
    <div className="container-fluid p-4">
      {/* Stats cards */}
      <div className="row">
        <div className="col-md-3 mb-4">
          <div className="card bg-primary text-white h-100">
            <div className="card-body">
              <div className="d-flex justify-content-between align-items-center">
                <div>
                  <h5 className="card-title">Total Students</h5>
                  <h2>{stats.totalStudents}</h2>
                </div>
                <i className="bi bi-people fs-1"></i>
              </div>
              <p className="card-text">Registered students</p>
            </div>
          </div>
        </div>
        <div className="col-md-3 mb-4">
          <div className="card bg-success text-white h-100">
            <div className="card-body">
              <div className="d-flex justify-content-between align-items-center">
                <div>
                  <h5 className="card-title">Total Staff</h5>
                  <h2>{stats.totalStaff}</h2>
                </div>
                <i className="bi bi-person-badge fs-1"></i>
              </div>
              <p className="card-text">Available staff</p>
            </div>
          </div>
        </div>
        <div className="col-md-3 mb-4">
          <div className="card bg-warning text-white h-100">
            <div className="card-body">
              <div className="d-flex justify-content-between align-items-center">
                <div>
                  <h5 className="card-title">Total Halls</h5>
                  <h2>{stats.totalHalls}</h2>
                </div>
                <i className="bi bi-building fs-1"></i>
              </div>
              <p className="card-text">Active halls</p>
            </div>
          </div>
        </div>
        <div className="col-md-3 mb-4">
          <div className="card bg-info text-white h-100">
            <div className="card-body">
              <div className="d-flex justify-content-between align-items-center">
                <div>
                  <h5 className="card-title">Upcoming Exams</h5>
                  <h2>{stats.upcomingExams}</h2>
                </div>
                <i className="bi bi-calendar-event fs-1"></i>
              </div>
              <p className="card-text">Scheduled exams</p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="row">
        <div className="col-md-8">
          <div className="card">
            <div className="card-header">
              <h5 className="card-title">Quick Actions</h5>
            </div>
            <div className="card-body">
              <div className="row">
                <div className="col-md-4 mb-3">
                  <button
                    className="btn btn-primary w-100"
                    onClick={() => handleQuickAction('students')}
                  >
                    <i className="bi bi-people me-2"></i>Add Students
                  </button>
                </div>
                <div className="col-md-4 mb-3">
                  <button
                    className="btn btn-secondary w-100"
                    onClick={() => handleQuickAction('staff')}
                  >
                    <i className="bi bi-person-badge me-2"></i>Add Staff
                  </button>
                </div>
                <div className="col-md-4 mb-3">
                  <button
                    className="btn btn-success w-100"
                    onClick={() => handleQuickAction('halls')}
                  >
                    <i className="bi bi-building me-2"></i>Manage Halls
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
