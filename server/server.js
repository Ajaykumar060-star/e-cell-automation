import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import 'express-async-errors';
import dotenv from 'dotenv';
import connectDB from './src/config/db.js';

// Routes
import studentRoutes from './src/routes/students.js';
import staffRoutes from './src/routes/staff.js';
import hallRoutes from './src/routes/halls.js';
import examRoutes from './src/routes/exams.js';
import attendanceRoutes from './src/routes/attendance.js';
import uploadRoutes from './src/routes/upload.js';
import seatingRoutes from './src/routes/seating.js';
import hallTicketRoutes from './src/routes/hallTickets.js';
import statsRoutes from './src/routes/stats.js';
import authRoutes from './src/routes/auth.js';

dotenv.config();

const app = express();
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Config
const PORT = process.env.PORT || 5000;
const CLIENT_ORIGIN = process.env.CLIENT_ORIGIN || 'http://localhost:3000';

// Middleware
app.use(cors({ origin: CLIENT_ORIGIN, credentials: true }));
app.use(helmet());
app.use(morgan('dev'));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Static for generated files (e.g., Excel outputs)
const outputsDir = path.join(__dirname, 'outputs');
if (!fs.existsSync(outputsDir)) {
  fs.mkdirSync(outputsDir, { recursive: true });
}
app.use('/outputs', express.static(outputsDir));

// Mount routes
app.use('/api/students', studentRoutes);
app.use('/api/staff', staffRoutes);
app.use('/api/halls', hallRoutes);
app.use('/api/exams', examRoutes);
app.use('/api/attendances', attendanceRoutes);
app.use('/api/auth', authRoutes);
app.use('/api/upload', uploadRoutes);
// support v2 path used by existing frontend
app.use('/api/v2/upload', uploadRoutes);
app.use('/api/seating', seatingRoutes);
app.use('/api/hall-tickets', hallTicketRoutes);
app.use('/api/stats', statsRoutes);

// Health
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', service: 'exam-management-mern-server' });
});

// 404 handler
app.use((req, res, next) => {
  res.status(404).json({ error: 'Not Found' });
});

// Error handler
// eslint-disable-next-line no-unused-vars
app.use((err, req, res, next) => {
  console.error('Unhandled error:', err);
  res.status(500).json({ error: err?.message || 'Internal Server Error' });
});

// Start
(async () => {
  try {
    await connectDB();
    app.listen(PORT, () => {
      console.log(`Server listening on http://localhost:${PORT}`);
    });
  } catch (err) {
    console.error('Failed to start server:', err);
    process.exit(1);
  }
})();
