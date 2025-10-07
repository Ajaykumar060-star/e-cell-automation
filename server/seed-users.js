import mongoose from 'mongoose';
import dotenv from 'dotenv';
import User from './src/models/User.js';

// Load environment variables
dotenv.config();

// Connect to MongoDB
const connectDB = async () => {
  const uri = process.env.MONGO_URI || 'mongodb://localhost:27017/exam_management';
  try {
    mongoose.set('strictQuery', true);
    await mongoose.connect(uri);
    console.log('✅ MongoDB connected for seeding');
  } catch (err) {
    console.error('❌ MongoDB connection error:', err.message);
    throw err;
  }
};

// Seed data
const seedUsers = async () => {
  try {
    // Clear existing users (optional - remove if you want to keep existing data)
    await User.deleteMany({});
    console.log('🗑️  Cleared existing users');

    // Create default admin user
    const adminUser = new User({
      username: 'admin',
      password: 'admin123', // This will be hashed by the pre-save hook
      role: 'admin',
      isActive: true
    });

    await adminUser.save();
    console.log('✅ Created admin user:');
    console.log('   Username: admin');
    console.log('   Password: admin123');
    console.log('   Role: admin');

    // Create a regular user (optional)
    const regularUser = new User({
      username: 'user',
      password: 'user123',
      role: 'user',
      isActive: true
    });

    await regularUser.save();
    console.log('✅ Created regular user:');
    console.log('   Username: user');
    console.log('   Password: user123');
    console.log('   Role: user');

    console.log('\n🎉 User seeding completed successfully!');
    console.log('\nYou can now:');
    console.log('1. Start the server: npm run dev');
    console.log('2. Access the frontend at http://localhost:3000');
    console.log('3. Login with admin/admin123 or user/user123');

  } catch (error) {
    console.error('❌ Error seeding users:', error);
  } finally {
    // Close database connection
    await mongoose.connection.close();
    console.log('🔌 Database connection closed');
  }
};

// Run the seed function
const runSeed = async () => {
  try {
    await connectDB();
    await seedUsers();
    process.exit(0);
  } catch (error) {
    console.error('❌ Seeding failed:', error);
    process.exit(1);
  }
};

// Execute seeding
console.log('🌱 Starting user data seeding...');
runSeed();
