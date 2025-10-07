import mongoose from 'mongoose';

const SeatingAllocationSchema = new mongoose.Schema(
  {
    hall_no: { type: Number, required: true },
    seat_no: { type: Number, required: true },
    reg_no: { type: String, required: true, index: true },
    name: { type: String, default: '' },
    sub_code: { type: String, default: '' },
    sub_title: { type: String, default: '' },
    class_code: { type: String, default: '' },
    dept: { type: String, default: '' },
    date: { type: String, required: true },
    sess: { type: String, required: true },
    hall_key: { type: String, required: true, index: true },
  },
  { timestamps: true }
);

SeatingAllocationSchema.index({ date: 1, sess: 1, hall_no: 1, seat_no: 1 }, { unique: true });

export default mongoose.model('SeatingAllocation', SeatingAllocationSchema);
