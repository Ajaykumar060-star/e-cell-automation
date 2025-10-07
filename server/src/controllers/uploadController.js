import fs from 'fs';
import path from 'path';
import Student from '../models/Student.js';
import Staff from '../models/Staff.js';
import Hall from '../models/Hall.js';
import SeatingAllocation from '../models/SeatingAllocation.js';
import { parseFile } from '../utils/parse.js';
import { normalizeRows } from '../utils/normalize.js';
import { allocateSeats } from '../utils/allocate.js';
import { generateAllocationExcel } from '../utils/excel.js';
import { getNextSequence } from '../utils/sequence.js';

function cleanPhone(p) {
  return String(p || '')
    .split('')
    .filter((ch) => ch >= '0' && ch <= '9')
    .join('')
    .slice(0, 10);
}

export const uploadStudents = async (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No file provided' });
  const filePath = req.file.path;
  try {
    const rows = await parseFile(filePath);
    let saved = 0;
    const errors = [];

    for (let i = 0; i < rows.length; i++) {
      const r = rows[i];
      const name = String(r.name || r.Name || '').trim();
      let email = String(r.email || r.Email || '').trim();
      const phone = cleanPhone(r.phone || r.Phone || '');
      const department = String(r.department || r.Department || '').trim();
      const year = String(r.year || r.Year || '').trim();
      const idVal = String(r.ID || r.id || '').trim();

      if (!email) {
        if (idVal) email = `${idVal}@example.edu`;
        else {
          errors.push(`Row ${i + 1}: Missing Email and ID`);
          continue;
        }
      }
      if (!name) {
        errors.push(`Row ${i + 1}: Missing Name`);
        continue;
      }

      const exists = await Student.findOne({ email });
      if (exists) {
        await Student.updateOne(
          { email },
          { $set: { name, phone, department, year } }
        );
      } else {
        const id = await getNextSequence('students');
        await Student.create({ id, name, email, phone, department, year });
      }
      saved += 1;
    }

    return res.json({ message: `Processed ${saved} students`, saved_students: saved, errors });
  } catch (err) {
    return res.status(500).json({ error: `Error processing file: ${err.message}` });
  } finally {
    try { fs.unlinkSync(filePath); } catch {}
  }
};

export const uploadStaff = async (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No file provided' });
  const filePath = req.file.path;
  try {
    const rows = await parseFile(filePath);
    let saved = 0;
    const errors = [];

    for (let i = 0; i < rows.length; i++) {
      const r = rows[i];
      const name = String(r.name || r.Name || '').trim();
      const email = String(r.email || r.Email || '').trim();
      const phone = cleanPhone(r.phone || r.Phone || '');
      const department = String(r.department || r.Department || '').trim();
      const role = String(r.role || r.Role || '').trim();

      if (!email || !name) {
        errors.push(`Row ${i + 1}: Missing required fields (name/email)`);
        continue;
      }

      const exists = await Staff.findOne({ email });
      if (exists) {
        await Staff.updateOne({ email }, { $set: { name, phone, department, role } });
      } else {
        await Staff.create({ name, email, phone, department, role });
      }
      saved += 1;
    }

    return res.json({ message: `Processed ${saved} staff`, saved_staff: saved, errors });
  } catch (err) {
    return res.status(500).json({ error: `Error processing file: ${err.message}` });
  } finally {
    try { fs.unlinkSync(filePath); } catch {}
  }
};

export const uploadHalls = async (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No file provided' });
  const filePath = req.file.path;
  try {
    const rows = await parseFile(filePath);
    let saved = 0;
    const errors = [];

    for (let i = 0; i < rows.length; i++) {
      const r = rows[i];
      const name = String(r.name || r.Name || '').trim();
      const capacity = Number(r.capacity || r.Capacity || 0);
      const location = String(r.location || r.Location || '').trim();
      const facilities = String(r.facilities || r.Facilities || '').trim();

      if (!name || !Number.isFinite(capacity) || capacity <= 0) {
        errors.push(`Row ${i + 1}: Missing/invalid hall name or capacity`);
        continue;
      }

      const exists = await Hall.findOne({ name });
      if (exists) {
        await Hall.updateOne({ name }, { $set: { capacity, location, facilities } });
      } else {
        await Hall.create({ name, capacity, location, facilities });
      }
      saved += 1;
    }

    return res.json({ message: `Processed ${saved} halls`, saved_halls: saved, errors });
  } catch (err) {
    return res.status(500).json({ error: `Error processing file: ${err.message}` });
  } finally {
    try { fs.unlinkSync(filePath); } catch {}
  }
};

export const uploadTimetable = async (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No file provided' });
  const filePath = req.file.path;
  const capacity = Number(req.body.capacity || 30);
  try {
    const rawRows = await parseFile(filePath);
    const normRows = normalizeRows(rawRows);
    const allocations = allocateSeats(normRows, capacity);

    // Save allocations to DB (overwrite strategy for same DATE+SESS? For now, insertMany)
    const docs = allocations.map((a) => ({
      hall_no: a.HALL_NO,
      seat_no: a.SEAT_NO,
      reg_no: a.REG_NO,
      name: a.NAME,
      sub_code: a.SUB_CODE,
      sub_title: a.SUB_TITLE,
      class_code: a.CLASS,
      dept: a.DEPT,
      date: a.DATE,
      sess: a.SESS,
      hall_key: a._HALL_KEY,
    }));
    await SeatingAllocation.insertMany(docs);

    const { filename } = await generateAllocationExcel(allocations);

    // Build preview (first 200)
    const preview = allocations.slice(0, 200).map((a) => ({
      HALL_NO: a.HALL_NO,
      SEAT_NO: a.SEAT_NO,
      REG_NO: a.REG_NO,
      NAME: a.NAME,
      SUB_CODE: a.SUB_CODE,
      SUB_TITLE: a.SUB_TITLE,
      CLASS: a.CLASS,
      DEPT: a.DEPT,
      DATE: a.DATE,
      SESS: a.SESS,
    }));

    // Summary
    const summaryMap = new Map();
    for (const a of allocations) {
      const key = `${a.SUB_CODE}||${a.SUB_TITLE}`;
      const entry = summaryMap.get(key) || { SUB_CODE: a.SUB_CODE, SUB_TITLE: a.SUB_TITLE, TOTAL_STUDENTS: 0, _HALLS: new Set() };
      entry.TOTAL_STUDENTS += 1;
      entry._HALLS.add(a._HALL_KEY);
      summaryMap.set(key, entry);
    }
    const summary = Array.from(summaryMap.values()).map((e) => ({
      SUB_CODE: e.SUB_CODE,
      SUB_TITLE: e.SUB_TITLE,
      TOTAL_STUDENTS: e.TOTAL_STUDENTS,
      HALLS_USED: e._HALLS.size,
    }));

    return res.json({
      message: `Generated allocation for ${allocations.length} rows`,
      processed_rows: normRows.length,
      saved_allocations: allocations.length,
      download_url: `/outputs/${filename}`,
      preview,
      summary,
    });
  } catch (err) {
    return res.status(500).json({ error: `Error processing file: ${err.message}` });
  } finally {
    try { fs.unlinkSync(filePath); } catch {}
  }
};
