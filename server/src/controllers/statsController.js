import Student from '../models/Student.js';
import Staff from '../models/Staff.js';
import Hall from '../models/Hall.js';
import Exam from '../models/Exam.js';
import Attendance from '../models/Attendance.js';
import SeatingAllocation from '../models/SeatingAllocation.js';

export const getCounts = async (req, res) => {
  const [students, staff, halls, exams, attendances] = await Promise.all([
    Student.countDocuments(),
    Staff.countDocuments(),
    Hall.countDocuments(),
    Exam.countDocuments(),
    Attendance.countDocuments(),
  ]);
  res.json({ students, staff, halls, exams, attendances });
};

export const subjectsSummary = async (req, res) => {
  const { date, sess } = req.query;
  const match = {};
  if (date) match.date = String(date);
  if (sess) match.sess = String(sess);

  const agg = await SeatingAllocation.aggregate([
    { $match: match },
    { $group: { _id: { sub: '$sub_code', title: '$sub_title' }, total: { $sum: 1 }, halls: { $addToSet: '$hall_key' } } },
    { $project: { _id: 0, SUB_CODE: '$_id.sub', SUB_TITLE: '$_id.title', TOTAL: '$total', HALLS_USED: { $size: '$halls' } } },
    { $sort: { SUB_CODE: 1, SUB_TITLE: 1 } }
  ]);
  res.json(agg);
};
