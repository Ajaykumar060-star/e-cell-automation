import React, { useState, useEffect } from 'react'
import api from '../services/api'
import '../styles/Reports.css'

const Reports = () => {
  const [reports, setReports] = useState({
    students: { total: 0, departments: {} },
    staff: { total: 0, departments: {} },
    halls: { total: 0, capacity: 0 },
    exams: { total: 0, upcoming: 0 }
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchReports()
  }, [])

  const fetchReports = async () => {
    try {
      const [studentsRes, staffRes, hallsRes, examsRes] = await Promise.all([
        api.get('/students/report'),
        api.get('/staff/report'),
        api.get('/halls/report'),
        api.get('/exams/report')
      ])

      setReports({
        students: studentsRes.data,
        staff: staffRes.data,
        halls: hallsRes.data,
        exams: examsRes.data
      })
    } catch (error) {
      console.error('Error fetching reports:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="container-fluid p-4">Loading reports...</div>
  }

  return (
    <div className="container-fluid p-4">
      <div className="row">
        <div className="col-md-12">
          <div className="card">
            <div className="card-header">
              <h4><i className="bi bi-graph-up me-2"></i>Reports & Summary</h4>
            </div>
            <div className="card-body">
              <div className="row">
                {/* Students Report */}
                <div className="col-md-6 mb-4">
                  <div className="card h-100">
                    <div className="card-header bg-primary text-white">
                      <h5 className="card-title mb-0"><i className="bi bi-people me-2"></i>Students</h5>
                    </div>
                    <div className="card-body">
                      <div className="row text-center">
                        <div className="col-6">
                          <h3 className="text-primary">{reports.students.total}</h3>
                          <p>Total Students</p>
                        </div>
                        <div className="col-6">
                          <h3 className="text-success">{Object.keys(reports.students.departments).length}</h3>
                          <p>Departments</p>
                        </div>
                      </div>
                      <div className="mt-3">
                        <h6>Department-wise Distribution:</h6>
                        <div className="table-responsive">
                          <table className="table table-sm">
                            <tbody>
                              {Object.entries(reports.students.departments).map(([dept, count]) => (
                                <tr key={dept}>
                                  <td>{dept}</td>
                                  <td className="text-end">{count}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Staff Report */}
                <div className="col-md-6 mb-4">
                  <div className="card h-100">
                    <div className="card-header bg-success text-white">
                      <h5 className="card-title mb-0"><i className="bi bi-person-badge me-2"></i>Staff</h5>
                    </div>
                    <div className="card-body">
                      <div className="row text-center">
                        <div className="col-6">
                          <h3 className="text-primary">{reports.staff.total}</h3>
                          <p>Total Staff</p>
                        </div>
                        <div className="col-6">
                          <h3 className="text-success">{Object.keys(reports.staff.departments).length}</h3>
                          <p>Departments</p>
                        </div>
                      </div>
                      <div className="mt-3">
                        <h6>Department-wise Distribution:</h6>
                        <div className="table-responsive">
                          <table className="table table-sm">
                            <tbody>
                              {Object.entries(reports.staff.departments).map(([dept, count]) => (
                                <tr key={dept}>
                                  <td>{dept}</td>
                                  <td className="text-end">{count}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Halls Report */}
                <div className="col-md-6 mb-4">
                  <div className="card h-100">
                    <div className="card-header bg-warning text-white">
                      <h5 className="card-title mb-0"><i className="bi bi-building me-2"></i>Halls</h5>
                    </div>
                    <div className="card-body">
                      <div className="row text-center">
                        <div className="col-6">
                          <h3 className="text-primary">{reports.halls.total}</h3>
                          <p>Total Halls</p>
                        </div>
                        <div className="col-6">
                          <h3 className="text-success">{reports.halls.capacity}</h3>
                          <p>Total Capacity</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Exams Report */}
                <div className="col-md-6 mb-4">
                  <div className="card h-100">
                    <div className="card-header bg-info text-white">
                      <h5 className="card-title mb-0"><i className="bi bi-calendar-event me-2"></i>Exams</h5>
                    </div>
                    <div className="card-body">
                      <div className="row text-center">
                        <div className="col-6">
                          <h3 className="text-primary">{reports.exams.total}</h3>
                          <p>Total Exams</p>
                        </div>
                        <div className="col-6">
                          <h3 className="text-success">{reports.exams.upcoming}</h3>
                          <p>Upcoming</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Reports
