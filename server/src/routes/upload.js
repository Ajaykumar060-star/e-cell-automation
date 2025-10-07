import { Router } from 'express';
import { upload } from '../middleware/upload.js';
import {
  uploadStudents,
  uploadStaff,
  uploadHalls,
  uploadTimetable,
} from '../controllers/uploadController.js';

const router = Router();

router.post('/students', upload.single('file'), uploadStudents);
router.post('/staff', upload.single('file'), uploadStaff);
router.post('/halls', upload.single('file'), uploadHalls);
router.post('/timetable', upload.single('file'), uploadTimetable);

export default router;
