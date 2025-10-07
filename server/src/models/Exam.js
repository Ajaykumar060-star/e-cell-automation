import mongoose from 'mongoose';

const ExamSchema = new mongoose.Schema(
  {
    subject: { type: String, required: true },
    date: { type: Date, required: true },
    time: { type: String, required: true }, // HH:MM
    duration: { type: Number, required: true }, // minutes or hours (follow your frontend)
    hall: { type: mongoose.Schema.Types.ObjectId, ref: 'Hall', required: true },
    staff: { type: mongoose.Schema.Types.ObjectId, ref: 'Staff', required: true },
    department: { type: String, default: '' },
    year: { type: String, default: '' },
    status: { type: String, default: 'upcoming' }
  },
  { timestamps: true }
);

// Prevent same hall at same date+time
ExamSchema.index({ hall: 1, date: 1, time: 1 }, { unique: true });

export default mongoose.model('Exam', ExamSchema);
