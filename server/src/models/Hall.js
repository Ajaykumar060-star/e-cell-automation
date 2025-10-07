import mongoose from 'mongoose';

const HallSchema = new mongoose.Schema(
  {
    name: { type: String, required: true, unique: true, index: true },
    capacity: { type: Number, required: true },
    location: { type: String, default: '' },
    facilities: { type: String, default: '' }
  },
  { timestamps: true }
);

export default mongoose.model('Hall', HallSchema);
