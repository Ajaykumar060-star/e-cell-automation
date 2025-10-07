import fs from 'fs';
import path from 'path';
import csv from 'csv-parser';
import * as XLSX from 'xlsx';

export async function parseFile(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === '.csv') {
    return await parseCSV(filePath);
  }
  if (ext === '.xlsx' || ext === '.xls') {
    return parseExcel(filePath);
  }
  throw new Error('Unsupported file format');
}

function parseExcel(filePath) {
  const wb = XLSX.readFile(filePath);
  const sheetName = wb.SheetNames[0];
  const sheet = wb.Sheets[sheetName];
  const rows = XLSX.utils.sheet_to_json(sheet, { defval: '' });
  return rows;
}

function parseCSV(filePath) {
  return new Promise((resolve, reject) => {
    const results = [];
    fs.createReadStream(filePath)
      .pipe(csv())
      .on('data', (data) => results.push(data))
      .on('end', () => resolve(results))
      .on('error', (err) => reject(err));
  });
}
