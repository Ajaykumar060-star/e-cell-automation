import React, { useState, useEffect } from 'react'
import api from '../services/api'
import '../styles/HallTickets.css'

const HallTickets = () => {
  const [exams, setExams] = useState([])
  const [selectedExam, setSelectedExam] = useState('')
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    fetchExams()
  }, [])

  const fetchExams = async () => {
    try {
      const response = await api.get('/exams')
      setExams(response.data)
    } catch (error) {
      console.error('Error fetching exams:', error)
    }
  }

  const fetchStudents = async (examId) => {
    setLoading(true)
    try {
      const response = await api.get(`/hall-tickets/students/${examId}`)
      setStudents(response.data)
    } catch (error) {
      console.error('Error fetching students:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleExamChange = (e) => {
    const examId = e.target.value
    setSelectedExam(examId)
    if (examId) {
      fetchStudents(examId)
    } else {
      setStudents([])
    }
  }

  const generateHallTickets = async () => {
    if (!selectedExam || students.length === 0) return

    setGenerating(true)
    try {
      const response = await api.post(`/hall-tickets/generate/${selectedExam}`)
      // Handle the response (could be file download)
      console.log('Hall tickets generated:', response.data)
    } catch (error) {
      console.error('Error generating hall tickets:', error)
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="container-fluid p-4">
      <div className="row">
        <div className="col-md-12">
          <div className="card">
            <div className="card-header">
              <h4><i className="bi bi-card-heading me-2"></i>Hall Ticket Generator</h4>
            </div>
            <div className="card-body">
              <div className="row mb-4">
                <div className="col-md-6">
                  <label htmlFor="examSelect" className="form-label">Select Exam</label>
                  <select
                    className="form-select"
                    id="examSelect"
                    value={selectedExam}
                    onChange={handleExamChange}
                  >
                    <option value="">Choose an exam...</option>
                    {exams.map((exam) => (
                      <option key={exam._id} value={exam._id}>
                        {exam.name} - {new Date(exam.date).toLocaleDateString()}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-md-6 d-flex align-items-end">
                  <button
                    className="btn btn-primary"
                    onClick={generateHallTickets}
                    disabled={!selectedExam || students.length === 0 || generating}
                  >
                    {generating ? 'Generating...' : 'Generate Hall Tickets'}
                  </button>
                </div>
              </div>

              {loading && <div className="text-center">Loading students...</div>}

              {students.length > 0 && (
                <div className="student-list">
                  <h5>Students for Selected Exam ({students.length} students)</h5>
                  <div className="table-responsive">
                    <table className="table table-striped">
                      <thead>
                        <tr>
                          <th>Roll No</th>
                          <th>Name</th>
                          <th>Department</th>
                          <th>Hall</th>
                          <th>Seat</th>
                        </tr>
                      </thead>
                      <tbody>
                        {students.map((student) => (
                          <tr key={student.rollNo}>
                            <td>{student.rollNo}</td>
                            <td>{student.name}</td>
                            <td>{student.department}</td>
                            <td>{student.hall || 'Not assigned'}</td>
                            <td>{student.seat || 'Not assigned'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default HallTickets
