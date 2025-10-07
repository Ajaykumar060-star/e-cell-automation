// Main JavaScript file for the Exam Management System

// Utility functions
function showNotification(message, type = "info") {
  // Create notification element
  const notification = document.createElement("div");
  notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
  notification.style.top = "20px";
  notification.style.right = "20px";
  notification.style.zIndex = "9999";
  notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

  // Add to body
  document.body.appendChild(notification);

  // Auto remove after 5 seconds
  setTimeout(() => {
    if (notification.parentNode) {
      notification.parentNode.removeChild(notification);
    }
  }, 5000);
}

function formatDate(dateString) {
  if (!dateString) return "";
  const date = new Date(dateString);
  return date.toLocaleDateString();
}

function formatDateTime(dateTimeString) {
  if (!dateTimeString) return "";
  const date = new Date(dateTimeString);
  return date.toLocaleString();
}

// Navigation functions
function loadStudents() {
  window.location.href = "/students";
}

function loadStaff() {
  window.location.href = "/staff";
}

function loadHalls() {
  window.location.href = "/halls";
}

function loadHallTickets() {
  window.location.href = "/hall_tickets";
}

function loadReports() {
  window.location.href = "/reports";
}

function loadAttendance() {
  window.location.href = "/attendance";
}

// API functions
const api = {
  // Students
  getStudents: () => fetch("/api/students").then((response) => response.json()),
  createStudent: (student) =>
    fetch("/api/students", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(student),
    }).then((response) => response.json()),
  updateStudent: (id, student) =>
    fetch(`/api/students/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(student),
    }).then((response) => response.json()),
  deleteStudent: (id) =>
    fetch(`/api/students/${id}`, {
      method: "DELETE",
    }).then((response) => {
      if (response.status === 204) return null;
      return response.json();
    }),

  // Staff
  getStaff: () => fetch("/api/staff").then((response) => response.json()),
  createStaff: (staff) =>
    fetch("/api/staff", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(staff),
    }).then((response) => response.json()),
  updateStaff: (id, staff) =>
    fetch(`/api/staff/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(staff),
    }).then((response) => response.json()),
  deleteStaff: (id) =>
    fetch(`/api/staff/${id}`, {
      method: "DELETE",
    }).then((response) => response.json()),

  // Halls
  getHalls: () => fetch("/api/halls").then((response) => response.json()),
  createHall: (hall) =>
    fetch("/api/halls", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(hall),
    }).then((response) => response.json()),
  updateHall: (id, hall) =>
    fetch(`/api/halls/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(hall),
    }).then((response) => response.json()),
  deleteHall: (id) =>
    fetch(`/api/halls/${id}`, {
      method: "DELETE",
    }).then((response) => response.json()),

  // Exams
  getExams: () => fetch("/api/exams").then((response) => response.json()),
  createExam: (exam) =>
    fetch("/api/exams", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(exam),
    }).then((response) => response.json()),

  // Attendance
  getAttendance: () =>
    fetch("/api/attendance").then((response) => response.json()),
  createAttendance: (attendance) =>
    fetch("/api/attendance", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(attendance),
    }).then((response) => response.json()),
};

// Form handling functions
function handleFormSubmit(formId, submitHandler) {
  const form = document.getElementById(formId);
  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      submitHandler(new FormData(form));
    });
  }
}

// Modal functions
function showModal(modalId) {
  const modal = new bootstrap.Modal(document.getElementById(modalId));
  modal.show();
}

function hideModal(modalId) {
  const modalElement = document.getElementById(modalId);
  const modal = bootstrap.Modal.getInstance(modalElement);
  if (modal) {
    modal.hide();
  }
}

// Export functions to global scope
window.showNotification = showNotification;
window.formatDate = formatDate;
window.formatDateTime = formatDateTime;
window.loadStudents = loadStudents;
window.loadStaff = loadStaff;
window.loadHalls = loadHalls;
window.loadHallTickets = loadHallTickets;
window.loadReports = loadReports;
window.loadAttendance = loadAttendance;
window.api = api;
window.handleFormSubmit = handleFormSubmit;
window.showModal = showModal;
window.hideModal = hideModal;
