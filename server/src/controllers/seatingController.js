import fs from 'fs';
import path from 'path';
import SeatingAllocation from '../models/SeatingAllocation.js';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const outputsDir = path.join(__dirname, '../../outputs');

export const listAllocations = async (req, res) => {
  const { date, sess, subject, page = 1, limit = 100 } = req.query;
  const q = {};
  if (date) q.date = String(date);
  if (sess) q.sess = String(sess);
  if (subject) q.sub_code = String(subject);

  const p = Math.max(1, Number(page));
  const l = Math.min(500, Math.max(1, Number(limit)));
  const [rows, total] = await Promise.all([
    SeatingAllocation.find(q).sort({ date: 1, sess: 1, hall_no: 1, seat_no: 1 }).skip((p - 1) * l).limit(l).lean(),
    SeatingAllocation.countDocuments(q),
  ]);
  res.json({ total, page: p, limit: l, rows });
};

export const summaryAllocations = async (req, res) => {
  const { date, sess } = req.query;
  const match = {};
  if (date) match.date = String(date);
  if (sess) match.sess = String(sess);

  const agg = await SeatingAllocation.aggregate([
    { $match: match },
    { $group: { _id: { sub: '$sub_code', title: '$sub_title' }, total: { $sum: 1 }, halls: { $addToSet: '$hall_key' } } },
    { $project: { _id: 0, SUB_CODE: '$_id.sub', SUB_TITLE: '$_id.title', TOTAL_STUDENTS: '$total', HALLS_USED: { $size: '$halls' } } },
    { $sort: { SUB_CODE: 1, SUB_TITLE: 1 } }
  ]);
  res.json(agg);
};

export const clearAllocations = async (req, res) => {
  await SeatingAllocation.deleteMany({});
  res.json({ message: 'All seating allocations cleared' });
};

export const latestOutput = async (req, res) => {
  if (!fs.existsSync(outputsDir)) return res.json({ filename: null });
  const files = fs.readdirSync(outputsDir).filter(f => f.endsWith('.xlsx'));
  if (files.length === 0) return res.json({ filename: null });
  files.sort((a, b) => fs.statSync(path.join(outputsDir, b)).mtimeMs - fs.statSync(path.join(outputsDir, a)).mtimeMs);
  res.json({ filename: files[0], url: `/outputs/${files[0]}` });
};
