import mongoose from 'mongoose';

const AttendanceSchema = new mongoose.Schema(
  {
    studentId: { type: Number, required: true, index: true },
    exam: { type: mongoose.Schema.Types.ObjectId, ref: 'Exam', required: true },
    status: { type: String, enum: ['Present', 'Absent', 'Late'], default: 'Present' },
    remarks: { type: String, default: '' }
  },
  { timestamps: true }
);

AttendanceSchema.index({ studentId: 1, exam: 1 }, { unique: true });

export default mongoose.model('Attendance', AttendanceSchema);
