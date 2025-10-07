import React, { useState, useEffect } from 'react'
import api from '../services/api'
import '../styles/SeatingPlan.css'

const SeatingPlan = () => {
  const [exams, setExams] = useState([])
  const [selectedExam, setSelectedExam] = useState('')
  const [seatingPlan, setSeatingPlan] = useState(null)
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

  const generateSeatingPlan = async () => {
    if (!selectedExam) return

    setGenerating(true)
    try {
      const response = await api.post(`/seating/generate/${selectedExam}`)
      setSeatingPlan(response.data)
    } catch (error) {
      console.error('Error generating seating plan:', error)
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
              <h4><i className="bi bi-diagram-3 me-2"></i>Generate Seating Plan</h4>
            </div>
            <div className="card-body">
              <div className="row mb-4">
                <div className="col-md-6">
                  <label htmlFor="examSelect" className="form-label">Select Exam</label>
                  <select
                    className="form-select"
                    id="examSelect"
                    value={selectedExam}
                    onChange={(e) => setSelectedExam(e.target.value)}
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
                    onClick={generateSeatingPlan}
                    disabled={!selectedExam || generating}
                  >
                    {generating ? 'Generating...' : 'Generate Seating Plan'}
                  </button>
                </div>
              </div>

              {seatingPlan && (
                <div className="seating-plan-results">
                  <h5>Seating Plan Results</h5>
                  <div className="row">
                    <div className="col-md-6">
                      <div className="card bg-light">
                        <div className="card-body">
                          <h6>Total Students Allocated: {seatingPlan.totalAllocated}</h6>
                          <h6>Total Halls Used: {seatingPlan.hallsUsed}</h6>
                          <h6>Staff Assigned: {seatingPlan.staffAssigned}</h6>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4">
                    <button className="btn btn-success">
                      <i className="bi bi-download me-2"></i>Download Seating Plan (Excel)
                    </button>
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

export default SeatingPlan
