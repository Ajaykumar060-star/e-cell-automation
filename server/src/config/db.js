import mongoose from 'mongoose';

const connectDB = async () => {
  const uri = process.env.MONGO_URI || 'mongodb://localhost:27017/exam_management';
  try {
    mongoose.set('strictQuery', true);
    await mongoose.connect(uri, {
      // opts kept minimal since Mongoose 8
    });
    console.log('MongoDB connected');
  } catch (err) {
    console.error('MongoDB connection error:', err.message);
    throw err;
  }
};

export default connectDB;
