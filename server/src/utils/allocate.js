// Seat allocation logic mirroring Flask exam_seating_app.allocate_seats

function normalizeSession(sess) {
  const s = String(sess || '').trim().toLowerCase();
  if (s === 'fn' || s === 'forenoon') return 'FN';
  if (s === 'an' || s === 'afternoon') return 'AN';
  return sess; // fallback
}

function sessionOrder(sess) {
  const s = String(sess || '').trim().toLowerCase();
  if (s === 'fn' || s === 'forenoon') return 0;
  if (s === 'an' || s === 'afternoon') return 1;
  return 99;
}

function parseDateFallback(d) {
  // Try day-first first, then month-first
  const a = new Date(d);
  if (!isNaN(a.getTime())) return a;
  // No robust alternative in plain JS; rely on sortable strings
  return new Date(d);
}

export function allocateSeats(rows, hallCapacity = 30) {
  const work = rows.map(r => ({
    REG_NO: String(r.REG_NO ?? ''),
    NAME: String(r.NAME ?? ''),
    SUB_CODE: String(r.SUB_CODE ?? ''),
    SUB_TITLE: String(r.SUB_TITLE ?? ''),
    CLASS: String(r.CLASS ?? ''),
    DEPT: String(r.DEPT ?? ''),
    DATE: String(r.DATE ?? ''),
    SESS: String(r.SESS ?? ''),
  }));

  // Precompute sort keys
  const augmented = work.map(r => ({
    ...r,
    _DATE_DT: parseDateFallback(r.DATE),
    _SESS_ORDER: sessionOrder(r.SESS),
  }));

  augmented.sort((a, b) => {
    const da = a._DATE_DT - b._DATE_DT;
    if (da !== 0) return da;
    const sa = a._SESS_ORDER - b._SESS_ORDER;
    if (sa !== 0) return sa;
    const sc = a.SUB_CODE.localeCompare(b.SUB_CODE);
    if (sc !== 0) return sc;
    return a.REG_NO.localeCompare(b.REG_NO);
  });

  const allocations = [];
  let hallNo = 1;
  let seatNo = 1;
  let lastKey = null;

  for (const row of augmented) {
    const date = row.DATE;
    const sess = normalizeSession(row.SESS) || row.SESS;
    const sessionKey = `${date}|${sess}`;
    if (sessionKey !== lastKey) {
      hallNo = 1;
      seatNo = 1;
      lastKey = sessionKey;
    }

    allocations.push({
      HALL_NO: hallNo,
      SEAT_NO: seatNo,
      REG_NO: row.REG_NO,
      NAME: row.NAME,
      SUB_CODE: row.SUB_CODE,
      SUB_TITLE: row.SUB_TITLE,
      CLASS: row.CLASS,
      DEPT: row.DEPT,
      DATE: date,
      SESS: sess,
      _HALL_KEY: `${date}-${sess}-H${hallNo}`,
    });

    seatNo += 1;
    if (seatNo > Number(hallCapacity || 30)) {
      hallNo += 1;
      seatNo = 1;
    }
  }

  return allocations;
}
