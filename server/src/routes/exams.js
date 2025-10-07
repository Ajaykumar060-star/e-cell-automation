import { Router } from 'express';
import {
  listExams,
  getExam,
  createExam,
  updateExam,
  deleteExam,
} from '../controllers/examsController.js';

const router = Router();

router.get('/', listExams);
router.get('/:id', getExam);
router.post('/', createExam);
router.put('/:id', updateExam);
router.delete('/:id', deleteExam);

export default router;
