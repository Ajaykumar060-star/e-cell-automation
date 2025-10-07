import { Router } from 'express';
import { getCounts, subjectsSummary } from '../controllers/statsController.js';

const router = Router();

router.get('/counts', getCounts);
router.get('/subjects', subjectsSummary);

export default router;
