import Staff from '../models/Staff.js';

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export const listStaff = async (req, res) => {
  const docs = await Staff.find().sort({ name: 1 }).lean();
  res.json(docs.map(({ _id, __v, ...rest }) => rest));
};

export const getStaff = async (req, res) => {
  const doc = await Staff.findById(req.params.id).lean();
  if (!doc) return res.status(404).json({ error: 'Staff not found' });
  const { _id, __v, ...rest } = doc;
  res.json(rest);
};

export const createStaff = async (req, res) => {
  const { name, email, phone, department, role } = req.body;
  if (!name || !email || !phone || !department || !role) {
    return res.status(400).json({ error: 'Missing required fields' });
  }
  if (!isValidEmail(email)) return res.status(400).json({ error: 'Invalid email format' });

  const exists = await Staff.findOne({ email });
  if (exists) return res.status(400).json({ error: 'Staff with this email already exists' });

  const doc = await Staff.create({ name, email, phone, department, role });
  res.status(201).json({ id: doc._id, name, email, phone, department, role });
};

export const updateStaff = async (req, res) => {
  const { name, email, phone, department, role } = req.body;
  if (!name || !email || !phone || !department || !role) {
    return res.status(400).json({ error: 'Missing required fields' });
  }
  if (!isValidEmail(email)) return res.status(400).json({ error: 'Invalid email format' });

  const other = await Staff.findOne({ email, _id: { $ne: req.params.id } });
  if (other) return res.status(400).json({ error: 'Staff with this email already exists' });

  const updated = await Staff.findByIdAndUpdate(
    req.params.id,
    { $set: { name, email, phone, department, role } },
    { new: true }
  ).lean();
  if (!updated) return res.status(404).json({ error: 'Staff not found' });
  const { _id, __v, ...rest } = updated;
  res.json(rest);
};

export const deleteStaff = async (req, res) => {
  const del = await Staff.deleteOne({ _id: req.params.id });
  if (del.deletedCount === 0) return res.status(404).json({ error: 'Staff not found' });
  res.status(204).send();
};
