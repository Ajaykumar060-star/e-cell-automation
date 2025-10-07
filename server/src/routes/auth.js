import express from 'express';
import { login, getMe } from '../controllers/authController.js';
import { protect } from '../middleware/auth.js';

const router = express.Router();

// Public routes
router.post('/login', login);

// Protected routes
router.get('/me', protect, getMe);

export default router;
