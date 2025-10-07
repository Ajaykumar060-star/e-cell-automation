import mongoose from 'mongoose';

const StudentSchema = new mongoose.Schema(
  {
    id: { type: Number, index: true, unique: true },
    name: { type: String, required: true },
    email: { type: String, required: true, index: true, unique: true },
    phone: { type: String, default: '' },
    department: { type: String, default: '' },
    year: { type: String, default: '' },
    created_at: { type: Date, default: Date.now }
  },
  { timestamps: true }
);

export default mongoose.model('Student', StudentSchema);
