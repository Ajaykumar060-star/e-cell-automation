import Student from '../models/Student.js';
import { getNextSequence } from '../utils/sequence.js';

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export const listStudents = async (req, res) => {
  const docs = await Student.find().sort({ id: 1 }).lean();
  res.json(docs.map(({ _id, __v, ...rest }) => rest));
};

export const getStudent = async (req, res) => {
  const idNum = Number(req.params.id);
  const doc = await Student.findOne({ id: idNum }).lean();
  if (!doc) return res.status(404).json({ error: 'Student not found' });
  const { _id, __v, ...rest } = doc;
  res.json(rest);
};

export const createStudent = async (req, res) => {
  const { name, email, phone, department, year } = req.body;
  if (!name || !email || !phone || !department || !year) {
    return res.status(400).json({ error: 'Missing required fields' });
  }
  if (!isValidEmail(email)) return res.status(400).json({ error: 'Invalid email format' });

  const exists = await Student.findOne({ email });
  if (exists) return res.status(400).json({ error: 'Student with this email already exists' });

  const id = await getNextSequence('students');
  const doc = await Student.create({ id, name, email, phone, department, year });
  res.status(201).json({ id: doc.id, name, email, phone, department, year, created_at: doc.created_at });
};

export const updateStudent = async (req, res) => {
  const idNum = Number(req.params.id);
  const { name, email, phone, department, year } = req.body;
  if (!name || !email || !phone || !department || !year) {
    return res.status(400).json({ error: 'Missing required fields' });
  }
  if (!isValidEmail(email)) return res.status(400).json({ error: 'Invalid email format' });

  const other = await Student.findOne({ email, id: { $ne: idNum } });
  if (other) return res.status(400).json({ error: 'Student with this email already exists' });

  const updated = await Student.findOneAndUpdate(
    { id: idNum },
    { $set: { name, email, phone, department, year } },
    { new: true }
  ).lean();
  if (!updated) return res.status(404).json({ error: 'Student not found' });
  const { _id, __v, ...rest } = updated;
  res.json(rest);
};

export const deleteStudent = async (req, res) => {
  const idNum = Number(req.params.id);
  const del = await Student.deleteOne({ id: idNum });
  if (del.deletedCount === 0) return res.status(404).json({ error: 'Student not found' });
  res.status(204).send();
};
