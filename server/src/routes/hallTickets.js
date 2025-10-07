import { Router } from 'express';
import { getStudentTickets, getSubjectTickets, getHallSession } from '../controllers/hallTicketsController.js';

const router = Router();

router.get('/student/:reg_no', getStudentTickets);
router.get('/subject/:sub_code', getSubjectTickets);
router.get('/:date/:sess/hall/:hall_no', getHallSession);

export default router;
