import SeatingAllocation from '../models/SeatingAllocation.js';

export const getStudentTickets = async (req, res) => {
  const reg = String(req.params.reg_no);
  const rows = await SeatingAllocation.find({ reg_no: reg })
    .sort({ date: 1, sess: 1, hall_no: 1, seat_no: 1 })
    .lean();
  res.json(rows.map(({ __v, _id, ...rest }) => rest));
};

export const getSubjectTickets = async (req, res) => {
  const sub = String(req.params.sub_code);
  const rows = await SeatingAllocation.find({ sub_code: sub })
    .sort({ date: 1, sess: 1, hall_no: 1, seat_no: 1 })
    .lean();
  res.json(rows.map(({ __v, _id, ...rest }) => rest));
};

export const getHallSession = async (req, res) => {
  const { date, sess, hall_no } = req.params;
  const q = { date: String(date), sess: String(sess), hall_no: Number(hall_no) };
  const rows = await SeatingAllocation.find(q).sort({ seat_no: 1 }).lean();
  res.json(rows.map(({ __v, _id, ...rest }) => rest));
};
