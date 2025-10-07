from __future__ import annotations
import os
import json
from typing import List, Dict, Any

from flask import Blueprint, request, jsonify, current_app, session
from werkzeug.utils import secure_filename
import pandas as pd
from pymongo import MongoClient

bp = Blueprint('students_v2', __name__, url_prefix='/api/v2')


def _get_mongo_db():
    # Try ems_app.extensions first
    try:
        from ems_app.extensions import mongo_db as _db
        if _db is not None:
            return _db
    except Exception:
        pass
    # Fallback: create a client from current_app config
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
    # Guard all v2 student endpoints with admin session check
    try:
        if 'admin_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
    except Exception:
        return jsonify({'error': 'Unauthorized'}), 401


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _build_16col_view(df: pd.DataFrame) -> pd.DataFrame:
    desired = [
        'SNO','ENQ','Reg_No','Name of the Student','Prog & Year','CLASS CODE','year','Degree','Dept',
        'DEPT ORD','CLASS ORD','SUB ORD','SUB_CODE','SUB_TITLE','DATE','SESS'
    ]
    cols_lower = {c.lower(): c for c in df.columns}

    def get_src(name: str):
        candidates = [
            name,
            name.replace('_', ' '),
            name.replace('&', 'and'),
            name.replace('  ', ' '),
        ]
        for cand in candidates:
            key = cand.strip().lower()
            if key in cols_lower:
                return cols_lower[key]
        return None

    data = {}
    for dc in desired:
        src = get_src(dc)
        data[dc] = df[src].astype(str) if src else ""
    return pd.DataFrame(data, columns=desired).fillna("")


@bp.route('/students', methods=['GET'])
def list_students_v2():
    """Return uploaded 16-column rows from JSON cache or Mongo fallback."""
    folder = _ensure_uploads_dir()
    json_path = os.path.join(folder, 'last_students.json')
    rows: List[Dict[str, Any]] = []
    try:
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                rows = json.load(f)
            return jsonify(rows)
    except Exception:
        pass

    # Fallback: try Mongo collection 'students_raw'
    db = _get_mongo_db()
    try:
        cur = db.get_collection('students_raw').find({}, {'_id': 0})
        rows = list(cur)
    except Exception:
        rows = []
    return jsonify(rows)


@bp.route('/upload/timetable', methods=['POST'])
def upload_timetable_v2():
    """Mongo-first upload: store raw rows and return subject grouping summary."""
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
        df = _normalize_columns(df)

        display_df = _build_16col_view(df)

        # Save JSON cache for UI
        json_path = os.path.join(folder, 'last_students.json')
        display_df.to_json(json_path, orient='records', force_ascii=False)
        session['last_students_json'] = json_path

        # Store raw docs to Mongo
        db = _get_mongo_db()
        docs = display_df.to_dict(orient='records')
        if docs:
            db.get_collection('students_raw').delete_many({})
            db.get_collection('students_raw').insert_many(docs)

        # Subject grouping summary
        subj_key = ['SUB_CODE', 'SUB_TITLE', 'DATE', 'SESS']
        summary_map: Dict[tuple, int] = {}
        for r in docs:
            key = tuple(r.get(k, '') for k in subj_key)
            summary_map[key] = summary_map.get(key, 0) + 1
        summary = [
            {
                'SUB_CODE': k[0], 'SUB_TITLE': k[1], 'DATE': k[2], 'SESS': k[3], 'TOTAL': v
            } for k, v in sorted(summary_map.items(), key=lambda x: (x[0][2], x[0][3], x[0][0]))
        ]

        return jsonify({
            'message': 'Timetable uploaded (Mongo-first)',
            'rows': len(docs),
            'summary': summary
        })
    except Exception as e:
        return jsonify({'error': f'Failed to process file: {e}'}), 500
    finally:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
