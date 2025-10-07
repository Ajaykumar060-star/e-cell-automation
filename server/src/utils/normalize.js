// Utilities to normalize timetable-like sheet columns

function norm(s) {
  return String(s || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '');
}

const ALIASES = {
  REG_NO: ['reg_no', 'reg no', 'register no', 'register_no', 'regno', 'roll', 'enr', 'enrollment no'],
  NAME: ['name of the student', 'student name', 'name'],
  SUB_CODE: ['sub_code', 'sub code', 'subject code', 'subject'],
  SUB_TITLE: ['sub_title', 'sub title', 'subject title', 'subject name', 'subname'],
  DATE: ['date', 'exam date', 'exam_date'],
  SESS: ['sess', 'session', 'session code'],
  CLASS: ['class code', 'class_code', 'class', 'classcode'],
  DEPT: ['dept', 'department', 'dept.'],
};

export function normalizeRows(rows) {
  if (!Array.isArray(rows) || rows.length === 0) return [];
  const keys = Object.keys(rows[0] || {});
  const normMap = {};
  for (const k of keys) normMap[norm(k)] = k;

  function resolve(key) {
    for (const cand of ALIASES[key]) {
      const nk = norm(cand);
      if (normMap[nk]) return normMap[nk];
    }
    return null;
  }

  const srcMap = {};
  for (const target of Object.keys(ALIASES)) {
    const src = resolve(target);
    if (src) srcMap[target] = src;
  }

  const out = rows.map((r) => ({
    REG_NO: String(r[srcMap.REG_NO] ?? ''),
    NAME: String(r[srcMap.NAME] ?? ''),
    SUB_CODE: String(r[srcMap.SUB_CODE] ?? ''),
    SUB_TITLE: String(r[srcMap.SUB_TITLE] ?? ''),
    DATE: String(r[srcMap.DATE] ?? ''),
    SESS: String(r[srcMap.SESS] ?? ''),
    CLASS: String(r[srcMap.CLASS] ?? ''),
    DEPT: String(r[srcMap.DEPT] ?? ''),
  }));

  const required = ['REG_NO', 'NAME', 'SUB_CODE', 'DATE', 'SESS'];
  const missing = required.filter((c) => out.every((r) => !String(r[c]).trim()));
  if (missing.length) throw new Error(`Missing required columns: ${missing.join(', ')}`);

  return out;
}
