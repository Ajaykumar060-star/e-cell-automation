# file: flask_mongo_exam.py
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from flask import Flask, request, jsonify
from pymongo import MongoClient, ASCENDING
from pymongo.errors import BulkWriteError
from pymongo import UpdateOne
import pandas as pd

# ----------------------------
# Configuration
# ----------------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "exam_management")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
students = db.students
exam_entries = db.exam_entries

# Ensure indexes
# Students unique on reg_no
students.create_index([("reg_no", ASCENDING)], unique=True)
# Exams unique per (reg_no, sub_code, exam_date, session)
exam_entries.create_index(
    [("reg_no", ASCENDING), ("sub_code", ASCENDING), ("exam_date", ASCENDING), ("session", ASCENDING)],
    unique=True
)
# Helpful query indexes
exam_entries.create_index([("sub_code", ASCENDING), ("exam_date", ASCENDING), ("session", ASCENDING)])
exam_entries.create_index([("hall_no", ASCENDING), ("exam_date", ASCENDING), ("session", ASCENDING)])

# ----------------------------
# Importer
# ----------------------------
def parse_date(raw) -> Optional[datetime]:
    if pd.isna(raw):
        return None
    if isinstance(raw, datetime):
        return raw
    s = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    # fallback: pandas to_datetime
    try:
        return pd.to_datetime(raw).to_pydatetime()
    except Exception:
        return None

def import_excel_to_mongo(file_path: str):
    # Read Excel (supports .xlsx, .xls). For CSV, use read_csv similarly.
    df = pd.read_excel(file_path, dtype=str) if file_path.lower().endswith((".xlsx", ".xls")) else pd.read_csv(file_path, dtype=str)

    # Normalize headers to lower-case, strip spaces/underscores
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Flexible resolvers (adjust if your headers differ)
    def col(*cands):
        for c in cands:
            if c in df.columns:
                return c
        return None

    reg_col = col("reg_no", "reg no", "regno", "register no", "register_no")
    name_col = col("name", "student_name", "name of the student")
    program_col = col("program", "prog", "course")
    class_code_col = col("class_code", "class code", "class")
    degree_col = col("degree")
    dept_col = col("dept", "department")

    sub_code_col = col("sub_code", "subject code", "sub code", "paper code")
    sub_title_col = col("sub_title", "subject title", "sub title", "paper title")
    exam_date_col = col("exam_date", "date")
    session_col = col("session", "sess")
    hall_no_col = col("hall_no", "hall no", "hall")
    seat_no_col = col("seat_no", "seat no", "seat")

    required = [reg_col, name_col, sub_code_col, sub_title_col, exam_date_col, session_col]
    if any(c is None for c in required):
        missing = []
        names_map = {
            "reg_no": reg_col, "name": name_col, "sub_code": sub_code_col, "sub_title": sub_title_col,
            "exam_date": exam_date_col, "session": session_col
        }
        for k, v in names_map.items():
            if v is None:
                missing.append(k)
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    # Build bulk ops
    student_ops: List[UpdateOne] = []
    exam_ops: List[UpdateOne] = []

    for _, row in df.iterrows():
        reg_no = str(row[reg_col]).strip()
        if not reg_no:
            continue

        student_doc = {
            "reg_no": reg_no,
            "name": str(row.get(name_col, "") or "").strip(),
            "program": str(row.get(program_col, "") or "").strip() if program_col else "",
            "class_code": str(row.get(class_code_col, "") or "").strip() if class_code_col else "",
            "degree": str(row.get(degree_col, "") or "").strip() if degree_col else "",
            "dept": str(row.get(dept_col, "") or "").strip() if dept_col else "",
        }
        # Upsert student (no duplicates)
        student_ops.append(
            UpdateOne({"reg_no": reg_no}, {"$set": student_doc}, upsert=True)
        )

        # Exam entry
        sub_code = str(row[sub_code_col]).strip()
        sub_title = str(row[sub_title_col]).strip()
        exam_date = parse_date(row[exam_date_col])
        sess = str(row[session_col]).strip().upper()
        hall_no = str(row[hall_no_col]).strip() if hall_no_col and pd.notna(row[hall_no_col]) else ""
        seat_no = str(row[seat_no_col]).strip() if seat_no_col and pd.notna(row[seat_no_col]) else ""

        exam_update_doc: Dict[str, Any] = {
            "reg_no": reg_no,
            "sub_code": sub_code,
            "sub_title": sub_title,
            "exam_date": exam_date,  # store as datetime
            "session": sess,
            "hall_no": hall_no,
            "seat_no": seat_no,
        }
        # Upsert exam entry keyed by (reg_no, sub_code, exam_date, session)
        exam_ops.append(
            UpdateOne(
                {"reg_no": reg_no, "sub_code": sub_code, "exam_date": exam_date, "session": sess},
                {"$set": exam_update_doc},
                upsert=True,
            )
        )

    # Execute in chunks for large datasets
    def bulk_exec(coll, ops: List[UpdateOne], chunk=2000):
        for i in range(0, len(ops), chunk):
            try:
                coll.bulk_write(ops[i:i+chunk], ordered=False)
            except BulkWriteError as bwe:
                # Ignore duplicate upsert races; log other errors
                errors = [e for e in bwe.details.get("writeErrors", []) if e.get("code") != 11000]
                if errors:
                    raise

    bulk_exec(students, student_ops)
    bulk_exec(exam_entries, exam_ops)

    return {
        "students_upserts": len(student_ops),
        "exam_upserts": len(exam_ops),
    }

# ----------------------------
# Flask app and routes
# ----------------------------
app = Flask(__name__)

@app.route("/import_excel", methods=["POST"])
def import_excel_endpoint():
    """
    POST multipart/form-data with 'file' field (Excel or CSV).
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400

    # Save temp and import
    tmp = os.path.join(os.getcwd(), f"upload_{int(datetime.now().timestamp())}_{f.filename}")
    f.save(tmp)
    try:
        result = import_excel_to_mongo(tmp)
        return jsonify({"message": "Import done", **result})
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass

@app.route("/hall_ticket/<reg_no>", methods=["GET"])
def hall_ticket(reg_no: str):
    stu = students.find_one({"reg_no": reg_no}, {"_id": 0})
    if not stu:
        return jsonify({"error": "Student not found"}), 404

    entries = list(exam_entries.find({"reg_no": reg_no}, {"_id": 0}).sort([("exam_date", ASCENDING), ("sub_code", ASCENDING)]))
    return jsonify({
        "student": stu,
        "exams": [
            {
                **e,
                "exam_date": e["exam_date"].isoformat() if isinstance(e.get("exam_date"), datetime) else e.get("exam_date")
            }
            for e in entries
        ]
    })

@app.route("/subject_list/<sub_code>", methods=["GET"])
def subject_list(sub_code: str):
    date_str = request.args.get("date")
    session = (request.args.get("session") or "").upper()
    if not date_str or not session:
        return jsonify({"error": "date and session are required"}), 400

    try:
        date_val = datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    query = {"sub_code": sub_code, "exam_date": date_val, "session": session}
    entries = list(exam_entries.find(query, {"_id": 0, "reg_no": 1}).sort([("reg_no", ASCENDING)]))

    # Lookup names (batch)
    reg_nos = [e["reg_no"] for e in entries]
    names = {s["reg_no"]: s.get("name", "") for s in students.find({"reg_no": {"$in": reg_nos}}, {"_id": 0, "reg_no": 1, "name": 1})}

    return jsonify([
        {"reg_no": r, "name": names.get(r, "")}
        for r in reg_nos
    ])

@app.route("/hall_list/<hall_no>", methods=["GET"])
def hall_list(hall_no: str):
    date_str = request.args.get("date")
    session = (request.args.get("session") or "").upper()
    if not date_str or not session:
        return jsonify({"error": "date and session are required"}), 400

    try:
        date_val = datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    query = {"hall_no": hall_no, "exam_date": date_val, "session": session}
    entries = list(exam_entries.find(query, {"_id": 0, "reg_no": 1, "seat_no": 1}).sort([("seat_no", ASCENDING)]))

    # Lookup names (batch)
    reg_nos = [e["reg_no"] for e in entries]
    names = {s["reg_no"]: s.get("name", "") for s in students.find({"reg_no": {"$in": reg_nos}}, {"_id": 0, "reg_no": 1, "name": 1})}

    return jsonify([
        {"reg_no": e["reg_no"], "name": names.get(e["reg_no"], ""), "seat_no": e.get("seat_no", "")}
        for e in entries
    ])

if __name__ == "__main__":
    # For quick test run
    app.run(host="127.0.0.1", port=5001, debug=True)