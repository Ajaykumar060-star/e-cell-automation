import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import '../styles/Login.css'

const Login = () => {
  const [credentials, setCredentials] = useState({
    username: '',
    password: ''
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleChange = (e) => {
    setCredentials({
      ...credentials,
      [e.target.name]: e.target.value
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const response = await api.post('/auth/login', credentials)
      localStorage.setItem('token', response.data.token)
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-container">
      <div className="login-form">
        <div className="logo">
          <i className="bi bi-mortarboard-fill"></i>
          <h3>Exam Management System</h3>
          <p className="text-muted">Admin Login</p>
        </div>

        {error && (
          <div className="alert alert-danger alert-dismissible fade show" role="alert">
            {error}
            <button
              type="button"
              className="btn-close"
              onClick={() => setError('')}
              aria-label="Close"
            ></button>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-3">
            <label htmlFor="username" className="form-label">Username</label>
            <div className="input-group">
              <span className="input-group-text"><i className="bi bi-person"></i></span>
              <input
                type="text"
                className="form-control"
                id="username"
                name="username"
                value={credentials.username}
                onChange={handleChange}
                required
              />
            </div>
          </div>
          <div className="mb-3">
            <label htmlFor="password" className="form-label">Password</label>
            <div className="input-group">
              <span className="input-group-text"><i className="bi bi-lock"></i></span>
              <input
                type="password"
                className="form-control"
                id="password"
                name="password"
                value={credentials.password}
                onChange={handleChange}
                required
              />
            </div>
          </div>
          <div className="d-grid">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Logging in...' : 'Login'}
            </button>
          </div>
        </form>

        <div className="mt-3 text-center">
          <small className="text-muted">
            <i className="bi bi-info-circle"></i> Default credentials: admin / admin123
          </small>
        </div>
      </div>
    </div>
  )
}

export default Login
