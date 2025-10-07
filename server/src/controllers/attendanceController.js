import Attendance from '../models/Attendance.js';
import Exam from '../models/Exam.js';

export const listAttendances = async (req, res) => {
  const docs = await Attendance.find().populate('exam').lean();
  res.json(docs.map(({ __v, ...rest }) => rest));
};

export const createAttendance = async (req, res) => {
  const { student_id, exam_id, status, remarks } = req.body;
  if (!student_id || !exam_id || !status) return res.status(400).json({ error: 'Missing required fields' });

  const exam = await Exam.findById(exam_id);
  if (!exam) return res.status(400).json({ error: 'Exam not found' });

  try {
    const doc = await Attendance.create({ studentId: Number(student_id), exam: exam._id, status, remarks: remarks || '' });
    res.status(201).json({ id: doc._id, studentId: doc.studentId, exam: doc.exam, status: doc.status, remarks: doc.remarks });
  } catch (err) {
    if (err?.code === 11000) return res.status(400).json({ error: 'Attendance record already exists for this student and exam' });
    throw err;
  }
};

export const getAttendance = async (req, res) => {
  const doc = await Attendance.findById(req.params.id).populate('exam').lean();
  if (!doc) return res.status(404).json({ error: 'Attendance record not found' });
  const { __v, ...rest } = doc;
  res.json(rest);
};

export const updateAttendance = async (req, res) => {
  const { student_id, exam_id, status, remarks } = req.body;
  const update = {};
  if (student_id) update.studentId = Number(student_id);
  if (exam_id) update.exam = exam_id;
  if (status) update.status = status;
  if (remarks !== undefined) update.remarks = remarks;

  const doc = await Attendance.findByIdAndUpdate(req.params.id, { $set: update }, { new: true }).lean();
  if (!doc) return res.status(404).json({ error: 'Attendance record not found' });
  const { __v, ...rest } = doc;
  res.json(rest);
};

export const deleteAttendance = async (req, res) => {
  const del = await Attendance.deleteOne({ _id: req.params.id });
  if (del.deletedCount === 0) return res.status(404).json({ error: 'Attendance not found' });
  res.status(204).send();
};
