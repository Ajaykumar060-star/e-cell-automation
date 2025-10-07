import mongoose from 'mongoose';

const StaffSchema = new mongoose.Schema(
  {
    name: { type: String, required: true },
    email: { type: String, required: true, unique: true, index: true },
    phone: { type: String, default: '' },
    department: { type: String, default: '' },
    role: { type: String, default: '' }
  },
  { timestamps: true }
);

export default mongoose.model('Staff', StaffSchema);
