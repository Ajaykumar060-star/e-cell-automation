import { Router } from 'express';
import {
  listAttendances,
  createAttendance,
  getAttendance,
  updateAttendance,
  deleteAttendance,
} from '../controllers/attendanceController.js';

const router = Router();

router.get('/', listAttendances);
router.post('/', createAttendance);
router.get('/:id', getAttendance);
router.put('/:id', updateAttendance);
router.delete('/:id', deleteAttendance);

export default router;
