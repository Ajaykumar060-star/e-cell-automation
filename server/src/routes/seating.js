import { Router } from 'express';
import { listAllocations, summaryAllocations, clearAllocations, latestOutput } from '../controllers/seatingController.js';

const router = Router();

router.get('/', listAllocations); // query: date, sess, subject, page, limit
router.get('/summary', summaryAllocations); // query: date, sess
router.delete('/', clearAllocations);
router.get('/latest-output', latestOutput);

export default router;
