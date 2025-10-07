import Counter from '../models/Counter.js';

export async function getNextSequence(name) {
  const doc = await Counter.findByIdAndUpdate(
    name,
    { $inc: { seq: 1 } },
    { upsert: true, new: true, setDefaultsOnInsert: true }
  );
  return doc.seq;
}
