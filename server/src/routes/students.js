import { Router } from 'express';
import {
  listStudents,
  getStudent,
  createStudent,
  updateStudent,
  deleteStudent,
} from '../controllers/studentsController.js';

const router = Router();

router.get('/', listStudents);
router.get('/:id', getStudent);
router.post('/', createStudent);
router.put('/:id', updateStudent);
router.delete('/:id', deleteStudent);

export default router;
