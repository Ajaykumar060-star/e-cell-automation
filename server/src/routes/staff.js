import { Router } from 'express';
import {
  listStaff,
  getStaff,
  createStaff,
  updateStaff,
  deleteStaff,
} from '../controllers/staffController.js';

const router = Router();

router.get('/', listStaff);
router.get('/:id', getStaff);
router.post('/', createStaff);
router.put('/:id', updateStaff);
router.delete('/:id', deleteStaff);

export default router;
