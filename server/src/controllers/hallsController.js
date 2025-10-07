import Hall from '../models/Hall.js';

export const listHalls = async (req, res) => {
  const halls = await Hall.find().sort({ name: 1 }).lean();
  res.json(halls.map(({ _id, __v, ...rest }) => rest));
};

export const createHall = async (req, res) => {
  const { name, capacity, location, facilities } = req.body;
  if (!name || !capacity) return res.status(400).json({ error: 'Missing required fields' });
  const cap = Number(capacity);
  if (!Number.isFinite(cap) || cap <= 0) return res.status(400).json({ error: 'Capacity must be a positive number' });
  const exists = await Hall.findOne({ name });
  if (exists) return res.status(400).json({ error: 'Hall with this name already exists' });
  const hall = await Hall.create({ name, capacity: cap, location: location || '', facilities: facilities || '' });
  res.status(201).json({ id: hall._id, name: hall.name, capacity: hall.capacity, location: hall.location, facilities: hall.facilities });
};

export const getHall = async (req, res) => {
  const hall = await Hall.findById(req.params.id).lean();
  if (!hall) return res.status(404).json({ error: 'Hall not found' });
  const { _id, __v, ...rest } = hall;
  res.json(rest);
};

export const updateHall = async (req, res) => {
  const { name, capacity, location, facilities } = req.body;
  const cap = Number(capacity);
  if (!name || !Number.isFinite(cap) || cap <= 0) return res.status(400).json({ error: 'Invalid payload' });
  const other = await Hall.findOne({ name, _id: { $ne: req.params.id } });
  if (other) return res.status(400).json({ error: 'Hall with this name already exists' });
  const updated = await Hall.findByIdAndUpdate(
    req.params.id,
    { $set: { name, capacity: cap, location: location || '', facilities: facilities || '' } },
    { new: true }
  ).lean();
  if (!updated) return res.status(404).json({ error: 'Hall not found' });
  const { _id, __v, ...rest } = updated;
  res.json(rest);
};

export const deleteHall = async (req, res) => {
  const del = await Hall.deleteOne({ _id: req.params.id });
  if (del.deletedCount === 0) return res.status(404).json({ error: 'Hall not found' });
  res.status(204).send();
};
