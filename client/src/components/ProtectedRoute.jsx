import React from 'react'
import { Navigate } from 'react-router-dom'

const ProtectedRoute = ({ children }) => {
  // For now, we'll assume user is authenticated
  // In a real app, you'd check authentication state
  const isAuthenticated = localStorage.getItem('token')

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return children
}

export default ProtectedRoute
