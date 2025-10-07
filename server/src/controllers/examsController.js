import Exam from '../models/Exam.js';
import Hall from '../models/Hall.js';
import Staff from '../models/Staff.js';

function parseDate(dateStr) {
  // Expect YYYY-MM-DD
  const d = new Date(dateStr);
  return isNaN(d.getTime()) ? null : d;
}

export const listExams = async (req, res) => {
  const exams = await Exam.find().populate('hall').populate('staff').lean();
  res.json(exams.map(({ __v, ...rest }) => rest));
};

export const getExam = async (req, res) => {
  const exam = await Exam.findById(req.params.id).populate('hall').populate('staff').lean();
  if (!exam) return res.status(404).json({ error: 'Exam not found' });
  const { __v, ...rest } = exam;
  res.json(rest);
};

export const createExam = async (req, res) => {
  const { subject, date, time, duration, hall_id, staff_id, department, year, status } = req.body;
  if (!subject || !date || !time || !duration || !hall_id || !staff_id || !department || !year) {
    return res.status(400).json({ error: 'Missing required fields' });
  }
  const d = parseDate(date);
  if (!d) return res.status(400).json({ error: 'Invalid date format (YYYY-MM-DD)' });
  const dur = Number(duration);
  if (!Number.isFinite(dur) || dur <= 0) return res.status(400).json({ error: 'Duration must be positive number' });

  const hall = await Hall.findById(hall_id);
  if (!hall) return res.status(400).json({ error: 'Hall not found' });
  const staff = await Staff.findById(staff_id);
  if (!staff) return res.status(400).json({ error: 'Staff not found' });

  // Enforce uniqueness (same hall, same date and time)
  const conflict = await Exam.findOne({ hall: hall._id, date: d, time });
  if (conflict) return res.status(400).json({ error: 'Hall is already booked for this date and time' });

  const doc = await Exam.create({
    subject,
    date: d,
    time,
    duration: dur,
    hall: hall._id,
    staff: staff._id,
    department,
    year,
    status: status || 'upcoming',
  });
  res.status(201).json({ id: doc._id, subject, date: doc.date, time: doc.time, duration: doc.duration, hall: hall._id, staff: staff._id, department, year, status: doc.status });
};

export const updateExam = async (req, res) => {
  const { subject, date, time, duration, hall_id, staff_id, department, year, status } = req.body;
  if (!subject || !date || !time || !duration || !hall_id || !staff_id || !department || !year) {
    return res.status(400).json({ error: 'Missing required fields' });
  }
  const d = parseDate(date);
  if (!d) return res.status(400).json({ error: 'Invalid date format (YYYY-MM-DD)' });
  const dur = Number(duration);
  if (!Number.isFinite(dur) || dur <= 0) return res.status(400).json({ error: 'Duration must be positive number' });

  const hall = await Hall.findById(hall_id);
  if (!hall) return res.status(400).json({ error: 'Hall not found' });
  const staff = await Staff.findById(staff_id);
  if (!staff) return res.status(400).json({ error: 'Staff not found' });

  const conflict = await Exam.findOne({ hall: hall._id, date: d, time, _id: { $ne: req.params.id } });
  if (conflict) return res.status(400).json({ error: 'Hall is already booked for this date and time' });

  const updated = await Exam.findByIdAndUpdate(
    req.params.id,
    { $set: { subject, date: d, time, duration: dur, hall: hall._id, staff: staff._id, department, year, status } },
    { new: true }
  ).lean();
  if (!updated) return res.status(404).json({ error: 'Exam not found' });
  const { __v, ...rest } = updated;
  res.json(rest);
};

export const deleteExam = async (req, res) => {
  const del = await Exam.deleteOne({ _id: req.params.id });
  if (del.deletedCount === 0) return res.status(404).json({ error: 'Exam not found' });
  res.status(204).send();
};
