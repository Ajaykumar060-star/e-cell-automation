import path from 'path';
import fs from 'fs';
import ExcelJS from 'exceljs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const outputsDir = path.join(__dirname, '../../outputs');
if (!fs.existsSync(outputsDir)) fs.mkdirSync(outputsDir, { recursive: true });

export async function generateAllocationExcel(allocations) {
  const workbook = new ExcelJS.Workbook();
  const sheetAlloc = workbook.addWorksheet('Allocation');
  const sheetSummary = workbook.addWorksheet('Summary');

  const allocCols = ['HALL_NO', 'SEAT_NO', 'REG_NO', 'NAME', 'SUB_CODE', 'SUB_TITLE', 'CLASS', 'DEPT', 'DATE', 'SESS'];
  sheetAlloc.columns = allocCols.map((k) => ({ header: k, key: k, width: 16 }));
  allocations.forEach((a) => {
    const row = {};
    allocCols.forEach((k) => (row[k] = a[k]));
    sheetAlloc.addRow(row);
  });

  // Build summary: TOTAL_STUDENTS and HALLS_USED per subject
  const summaryMap = new Map();
  for (const a of allocations) {
    const key = `${a.SUB_CODE}||${a.SUB_TITLE}`;
    const entry = summaryMap.get(key) || { SUB_CODE: a.SUB_CODE, SUB_TITLE: a.SUB_TITLE, TOTAL_STUDENTS: 0, _HALLS: new Set() };
    entry.TOTAL_STUDENTS += 1;
    entry._HALLS.add(a._HALL_KEY);
    summaryMap.set(key, entry);
  }
  const summaryRows = Array.from(summaryMap.values()).map((e) => ({
    SUB_CODE: e.SUB_CODE,
    SUB_TITLE: e.SUB_TITLE,
    TOTAL_STUDENTS: e.TOTAL_STUDENTS,
    HALLS_USED: e._HALLS.size,
  })).sort((a,b) => (a.SUB_CODE + a.SUB_TITLE).localeCompare(b.SUB_CODE + b.SUB_TITLE));

  const summaryCols = ['SUB_CODE', 'SUB_TITLE', 'TOTAL_STUDENTS', 'HALLS_USED'];
  sheetSummary.columns = summaryCols.map((k) => ({ header: k, key: k, width: 22 }));
  summaryRows.forEach((r) => sheetSummary.addRow(r));

  const ts = new Date().toISOString().replace(/[-:TZ.]/g, '').slice(0, 14);
  const filename = `seating_allocation_${ts}.xlsx`;
  const outPath = path.join(outputsDir, filename);
  await workbook.xlsx.writeFile(outPath);
  return { filename, outPath };
}
