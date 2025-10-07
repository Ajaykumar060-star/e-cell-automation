from __future__ import annotations
import os
from typing import List, Dict, Any, Tuple
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app, Response
from werkzeug.utils import secure_filename
import pandas as pd
from pymongo import MongoClient
from bson.objectid import ObjectId

bp = Blueprint('allocation_v2', __name__, url_prefix='/api/v2')


def _get_mongo_db():
    try:
        from ems_app.extensions import mongo_db as _db
        if _db is not None:
            return _db
    except Exception:
        pass
    uri = current_app.config.get('MONGO_URI', 'mongodb://localhost:27017')
    db_name = current_app.config.get('MONGO_DB_NAME', 'exam_management')
    client = MongoClient(uri)
    return client[db_name]


def _ensure_uploads_dir() -> str:
    folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(folder, exist_ok=True)
    return folder


@bp.before_request
def _require_admin():
    try:
        from flask import session
        if 'admin_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
    except Exception:
        return jsonify({'error': 'Unauthorized'}), 401


def _parse_date(value: str) -> str:
    # Return as ISO yyyy-mm-dd
    if not value:
        raise ValueError('Empty date')
    value = str(value).strip()
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except Exception:
            continue
    # Try pandas
    try:
        return pd.to_datetime(value).date().isoformat()
    except Exception:
        raise ValueError(f'Unrecognized date format: {value}')


@bp.route('/upload/halls', methods=['POST'])
def upload_halls_v2():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    folder = _ensure_uploads_dir()
    filename = secure_filename(file.filename)
    path = os.path.join(folder, filename)
    file.save(path)

    try:
        if filename.lower().endswith('.csv'):
            df = pd.read_csv(path, dtype=str)
        else:
            df = pd.read_excel(path, dtype=str)
        df.columns = [str(c).strip().lower() for c in df.columns]

        # Resolve columns
        def res(*names):
            for n in names:
                n = str(n).strip().lower()
                if n in df.columns:
                    return n
            return None

        name_col = res('name', 'hall', 'hall name', 'hall_name')
        cap_col = res('capacity', 'cap')
        loc_col = res('location', 'block', 'room', 'building')
        if not name_col or not cap_col:
            return jsonify({'error': 'Missing required columns: name, capacity'}), 400

        docs: List[Dict[str, Any]] = []
        for _, r in df.iterrows():
            name = str(r[name_col]).strip()
            if not name:
                continue
            try:
                capacity = int(str(r[cap_col]).strip())
            except Exception:
                capacity = 0
            doc = {
                'name': name,
                'capacity': max(capacity, 0),
                'location': (str(r[loc_col]).strip() if loc_col else ''),
            }
            docs.append(doc)

        if not docs:
            return jsonify({'error': 'No valid hall rows found'}), 400

        db = _get_mongo_db()
        halls = db.get_collection('halls')
        # Simple strategy: replace all
        halls.delete_many({})
        halls.insert_many(docs)

        return jsonify({'message': 'Halls uploaded', 'count': len(docs)})
    except Exception as e:
        return jsonify({'error': f'Failed to process halls: {e}'}), 500
    finally:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass


@bp.route('/allocate', methods=['POST'])
def allocate_v2():
    """Allocate seats from students_raw to halls by subject for a given DATE+SESS.
    Body JSON: { "date": "YYYY-MM-DD" or "DD-MM-YYYY", "session": "FN|AN|EV" }
    """
    data = request.get_json(silent=True) or {}
    date_in = (data.get('date') or '').strip()
    sess = (data.get('session') or '').strip().upper()
    if not date_in or not sess:
        return jsonify({'error': 'date and session are required'}), 400

    try:
        iso_date = _parse_date(date_in)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    db = _get_mongo_db()
    halls = list(db.get_collection('halls').find({}, {'_id': 1, 'name': 1, 'capacity': 1, 'location': 1}).sort('capacity', -1))
    if not halls:
        return jsonify({'error': 'No halls available'}), 400

    # Load students for this slot from cache
    rows = list(db.get_collection('students_raw').find({'DATE': iso_date, 'SESS': sess}, {'_id': 0}))
    if not rows:
        # Try accepting non-normalized dates; collect matches where DATE equals original input
        rows = list(db.get_collection('students_raw').find({'DATE': date_in, 'SESS': sess}, {'_id': 0}))
    if not rows:
        return jsonify({'error': 'No student rows found for given date/session'}), 404

    # Group by subject
    from collections import defaultdict
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        key = (str(r.get('SUB_CODE', '')), str(r.get('SUB_TITLE', '')))
        groups[key].append(r)

    # Ensure we have enough capacity overall
    total_capacity = sum(int(h.get('capacity') or 0) for h in halls)

    results = []
    created_slots = []

    for (sub_code, sub_title), items in groups.items():
        # Sort by Reg_No ascending (string compare; if numeric, still stable)
        items_sorted = sorted(items, key=lambda x: (str(x.get('Reg_No', '')).zfill(20)))
        n = len(items_sorted)
        if n > total_capacity:
            return jsonify({'error': f'Not enough capacity to allocate {n} students for subject {sub_code} on {iso_date} {sess}',
                            'needed': n, 'capacity': total_capacity}), 400

        # Create exam_slot doc
        slot_doc = {
            'date': iso_date,
            'session': sess,
            'subject_code': sub_code,
            'subject_title': sub_title,
            'halls_used': [],
            'created_at': datetime.utcnow()
        }
        slot_id = db.get_collection('exam_slots').insert_one(slot_doc).inserted_id

        # Allocate across halls
        remaining = list(items_sorted)
        for hall in halls:
            if not remaining:
                break
            cap = int(hall.get('capacity') or 0)
            if cap <= 0:
                continue
            take = min(len(remaining), cap)
            allocated = remaining[:take]
            remaining = remaining[take:]

            # Create seat docs 1..take for this hall
            seat_docs = []
            for i, row in enumerate(allocated, start=1):
                seat_docs.append({
                    'exam_slot_id': slot_id,
                    'date': iso_date,
                    'session': sess,
                    'hall_id': hall['_id'],
                    'hall_name': hall.get('name', ''),
                    'seat_no': i,
                    'reg_no': row.get('Reg_No', ''),
                    'student_name': row.get('Name of the Student', ''),
                    'dept': row.get('Dept', ''),
                    'sub_code': sub_code,
                    'sub_title': sub_title,
                })
            if seat_docs:
                db.get_collection('hall_seats').insert_many(seat_docs)
                db.get_collection('exam_slots').update_one({'_id': slot_id}, {
                    '$push': {'halls_used': {
                        'hall_id': hall['_id'],
                        'hall_name': hall.get('name', ''),
                        'allocated': len(seat_docs)
                    }}
                })

        results.append({
            'subject_code': sub_code,
            'subject_title': sub_title,
            'exam_slot_id': str(slot_id),
        })
        created_slots.append(slot_id)

    return jsonify({
        'message': 'Allocation completed (Mongo)',
        'date': iso_date,
        'session': sess,
        'subjects': results,
        'slots_created': [str(x) for x in created_slots]
    })


@bp.route('/export/halltickets', methods=['GET'])
def export_hall_tickets_v2():
    """Export hall tickets for a date/session.
    Query: ?date=YYYY-MM-DD&session=FN|AN&format=xlsx|pdf
    """
    date_in = (request.args.get('date') or '').strip()
    sess = (request.args.get('session') or '').strip().upper()
    fmt = (request.args.get('format') or 'xlsx').strip().lower()
    if not date_in or not sess:
        return jsonify({'error': 'date and session are required'}), 400
    try:
        iso_date = _parse_date(date_in)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    db = _get_mongo_db()
    seats = list(db.get_collection('hall_seats').find(
        {'date': iso_date, 'session': sess},
        {'_id': 0}
    ).sort([('hall_name', 1), ('seat_no', 1)]))
    if not seats:
        return jsonify({'error': 'No hall seats found for given date/session'}), 404

    if fmt == 'xlsx':
        import pandas as pd
        from io import BytesIO
        buf = BytesIO()
        df = pd.DataFrame(seats)
        # Arrange columns nicely
        cols = ['reg_no','student_name','dept','sub_code','sub_title','date','session','hall_name','seat_no']
        df = df[[c for c in cols if c in df.columns]]
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='HallTickets')
        buf.seek(0)
        fname = f"halltickets_{iso_date}_{sess}.xlsx"
        return Response(buf.getvalue(), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        headers={'Content-Disposition': f'attachment; filename={fname}'})

    if fmt == 'pdf':
        from io import BytesIO
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import mm
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        W, H = A4
        for r in seats:
            c.setFont('Helvetica-Bold', 14)
            c.drawString(20*mm, H-20*mm, 'HALL TICKET')
            c.setFont('Helvetica', 11)
            y = H-30*mm
            lines = [
                f"Name: {r.get('student_name','')}",
                f"Reg No: {r.get('reg_no','')}",
                f"Dept: {r.get('dept','')}",
                f"Subject: {r.get('sub_code','')} - {r.get('sub_title','')}",
                f"Date/Session: {r.get('date','')} {r.get('session','')}",
                f"Hall/Seat: {r.get('hall_name','')} / {r.get('seat_no','')}",
            ]
            for line in lines:
                c.drawString(20*mm, y, line)
                y -= 7*mm
            c.showPage()
        c.save()
        pdf_bytes = buf.getvalue()
        fname = f"halltickets_{iso_date}_{sess}.pdf"
        return Response(pdf_bytes, mimetype='application/pdf',
                        headers={'Content-Disposition': f'attachment; filename={fname}'})

    return jsonify({'error': 'Invalid format. Use xlsx or pdf'}), 400


@bp.route('/export/attendance', methods=['GET'])
def export_attendance_v2():
    """Export attendance list per hall for a date/session.
    Query: ?date=YYYY-MM-DD&session=FN|AN&format=xlsx|html
    """
    date_in = (request.args.get('date') or '').strip()
    sess = (request.args.get('session') or '').strip().upper()
    fmt = (request.args.get('format') or 'xlsx').strip().lower()
    if not date_in or not sess:
        return jsonify({'error': 'date and session are required'}), 400
    try:
        iso_date = _parse_date(date_in)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    db = _get_mongo_db()
    seats = list(db.get_collection('hall_seats').find(
        {'date': iso_date, 'session': sess},
        {'_id': 0}
    ).sort([('hall_name', 1), ('seat_no', 1)]))
    if not seats:
        return jsonify({'error': 'No hall seats found for given date/session'}), 404

    # Prepare grouped by hall
    from collections import defaultdict
    halls = defaultdict(list)
    for r in seats:
        halls[r.get('hall_name','')].append(r)

    if fmt == 'xlsx':
        import pandas as pd
        from io import BytesIO
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            for hall_name, rows in halls.items():
                df = pd.DataFrame(rows)
                df = df[['seat_no','reg_no','student_name','sub_code','sub_title']]
                df.rename(columns={'seat_no': 'S.No', 'student_name': 'Name of the Student', 'sub_code': 'Subject', 'sub_title': 'Subject Title'}, inplace=True)
                df.to_excel(writer, index=False, sheet_name=(hall_name or 'Hall')[:31])
        buf.seek(0)
        fname = f"attendance_{iso_date}_{sess}.xlsx"
        return Response(buf.getvalue(), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        headers={'Content-Disposition': f'attachment; filename={fname}'})

    if fmt == 'html':
        # Simple printable HTML
        html_parts = ["<html><head><title>Attendance</title></head><body>"]
        html_parts.append(f"<h2>Attendance {iso_date} {sess}</h2>")
        for hall_name, rows in halls.items():
            html_parts.append(f"<h3>Hall: {hall_name}</h3>")
            html_parts.append('<table border="1" cellspacing="0" cellpadding="5">')
            html_parts.append('<thead><tr><th>S.No</th><th>Reg_No</th><th>Name of the Student</th><th>Subject</th><th>Signature</th></tr></thead><tbody>')
            for r in rows:
                html_parts.append(
                    f"<tr><td>{r.get('seat_no','')}</td><td>{r.get('reg_no','')}</td><td>{r.get('student_name','')}</td><td>{r.get('sub_code','')}</td><td></td></tr>"
                )
            html_parts.append('</tbody></table><br>')
        html_parts.append("</body></html>")
        return Response("\n".join(html_parts), mimetype='text/html')

    return jsonify({'error': 'Invalid format. Use xlsx or html'}), 400
