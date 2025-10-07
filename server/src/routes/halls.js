import { Router } from 'express';
import {
  listHalls,
  createHall,
  getHall,
  updateHall,
  deleteHall,
} from '../controllers/hallsController.js';

const router = Router();

router.get('/', listHalls);
router.post('/', createHall);
router.get('/:id', getHall);
router.put('/:id', updateHall);
router.delete('/:id', deleteHall);

export default router;
