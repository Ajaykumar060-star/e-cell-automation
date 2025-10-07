import React, { useState } from 'react'
import api from '../services/api'
import '../styles/Upload.css'

const UploadStaff = () => {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState('')

  const handleFileChange = (e) => {
    setFile(e.target.files[0])
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    if (!file) return

    setUploading(true)
    setMessage('')

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await api.post('/upload/staff', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      setMessage(`Success: ${response.data.message}`)
    } catch (error) {
      setMessage(`Error: ${error.response?.data?.message || 'Upload failed'}`)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="container-fluid p-4">
      <div className="row justify-content-center">
        <div className="col-md-8">
          <div className="card">
            <div className="card-header">
              <h4><i className="bi bi-person-badge me-2"></i>Upload Staff</h4>
            </div>
            <div className="card-body">
              <form onSubmit={handleUpload}>
                <div className="mb-3">
                  <label htmlFor="staffFile" className="form-label">
                    Select CSV file containing staff data
                  </label>
                  <input
                    type="file"
                    className="form-control"
                    id="staffFile"
                    accept=".csv"
                    onChange={handleFileChange}
                    required
                  />
                </div>

                {file && (
                  <div className="mb-3">
                    <p><strong>Selected file:</strong> {file.name}</p>
                    <p><strong>Size:</strong> {(file.size / 1024).toFixed(2)} KB</p>
                  </div>
                )}

                <div className="d-grid">
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={!file || uploading}
                  >
                    {uploading ? 'Uploading...' : 'Upload Staff'}
                  </button>
                </div>
              </form>

              {message && (
                <div className={`mt-3 alert ${message.includes('Error') ? 'alert-danger' : 'alert-success'}`}>
                  {message}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default UploadStaff
