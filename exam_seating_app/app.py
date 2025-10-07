import os
import uuid
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename
import pandas as pd

# ---------------------------------------------------------
# Flask setup
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _norm(s: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "", str(s).strip().lower())


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize input columns to a common schema.

    Expected aliases present in the input (case/space insensitive):
      - REG_NO: Reg_No, Reg No, Register No, RegNo, etc.
      - NAME: Name of the Student, Student Name, Name
      - SUB_CODE: SUB_CODE, Subject Code, Subject
      - SUB_TITLE: SUB_TITLE, Subject Title, Subject Name
      - DATE: DATE, Exam Date
      - SESS: SESS, Session
      - CLASS: CLASS CODE, Class, Class Code
      - DEPT: Dept, Department
    """
    aliases = {
        'REG_NO': ['reg_no', 'reg no', 'register no', 'register_no', 'regno', 'roll', 'enr', 'enrollment no'],
        'NAME': ['name of the student', 'student name', 'name'],
        'SUB_CODE': ['sub_code', 'sub code', 'subject code', 'subject'],
        'SUB_TITLE': ['sub_title', 'sub title', 'subject title', 'subject name', 'subname'],
        'DATE': ['date', 'exam date', 'exam_date'],
        'SESS': ['sess', 'session', 'session code'],
        'CLASS': ['class code', 'class_code', 'class'],
        'DEPT': ['dept', 'department', 'dept.']
    }

    norm_map = {_norm(c): c for c in df.columns}

    def resolve(key: str):
        for cand in aliases[key]:
            k = _norm(cand)
            if k in norm_map:
                return norm_map[k]
        return None

    col_map = {}
    for target in aliases.keys():
        src = resolve(target)
        if src:
            col_map[target] = src

    # Build normalized dataframe with required columns
    out = pd.DataFrame()
    out['REG_NO'] = df[col_map['REG_NO']].astype(str) if 'REG_NO' in col_map else ''
    out['NAME'] = df[col_map['NAME']].astype(str) if 'NAME' in col_map else ''
    out['SUB_CODE'] = df[col_map['SUB_CODE']].astype(str) if 'SUB_CODE' in col_map else ''
    out['SUB_TITLE'] = df[col_map['SUB_TITLE']].astype(str) if 'SUB_TITLE' in col_map else ''
    out['DATE'] = df[col_map['DATE']].astype(str) if 'DATE' in col_map else ''
    out['SESS'] = df[col_map['SESS']].astype(str) if 'SESS' in col_map else ''
    out['CLASS'] = df[col_map['CLASS']].astype(str) if 'CLASS' in col_map else ''
    out['DEPT'] = df[col_map['DEPT']].astype(str) if 'DEPT' in col_map else ''

    # Clean common NaNs
    out = out.fillna("")

    # Validate minimal required columns
    required = ['REG_NO', 'NAME', 'SUB_CODE', 'DATE', 'SESS']
    missing = [c for c in required if out[c].eq("").all()]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    return out


def allocate_seats(df: pd.DataFrame, hall_capacity: int = 30) -> pd.DataFrame:
    """Allocate seats by DATE+SESS, sorted by SUB_CODE then REG_NO.

    Rules:
    - Sort by DATE (chronologically), SESS (FN before AN), then SUB_CODE, then REG_NO.
    - For each session (DATE+SESS), start with Hall 1, Seat 1 and increment.
    - When a hall reaches capacity, move to the next hall and restart seat numbering.
    """
    work = df.copy()

    # Parse date for sorting, prefer day-first then fall back
    dt = pd.to_datetime(work['DATE'], errors='coerce', dayfirst=True)
    dt2 = pd.to_datetime(work['DATE'], errors='coerce', dayfirst=False)
    work['_DATE_DT'] = dt.fillna(dt2)

    sess_order_map = {"fn": 0, "an": 1}
    work['_SESS_ORDER'] = work['SESS'].astype(str).str.strip().str.lower().map(sess_order_map).fillna(99)

    # Standardize REG_NO to string for sort stability
    work['REG_NO'] = work['REG_NO'].astype(str)
    work['SUB_CODE'] = work['SUB_CODE'].astype(str)

    work = work.sort_values(by=['_DATE_DT', '_SESS_ORDER', 'SUB_CODE', 'REG_NO'], kind='mergesort').reset_index(drop=True)

    # Allocate per session
    allocations = []
    for (date, sess), g in work.groupby(['DATE', 'SESS'], sort=False):
        hall_no = 1
        seat_no = 1
        for _, row in g.iterrows():
            allocations.append({
                'HALL_NO': hall_no,
                'SEAT_NO': seat_no,
                'REG_NO': row['REG_NO'],
                'NAME': row.get('NAME', ''),
                'SUB_CODE': row.get('SUB_CODE', ''),
                'SUB_TITLE': row.get('SUB_TITLE', ''),
                'CLASS': row.get('CLASS', ''),
                'DEPT': row.get('DEPT', ''),
                'DATE': date,
                'SESS': sess,
                # Unique hall key across sessions for summary
                '_HALL_KEY': f"{date}-{sess}-H{hall_no}",
            })
            seat_no += 1
            if seat_no > hall_capacity:
                hall_no += 1
                seat_no = 1

    alloc_df = pd.DataFrame(allocations)
    return alloc_df


def generate_excel(alloc_df: pd.DataFrame) -> str:
    """Save allocation and summary to an Excel file under outputs/ and return filename."""
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"seating_allocation_{ts}.xlsx"
    out_path = os.path.join(OUTPUT_FOLDER, filename)

    # Build summary: total students and halls used per subject
    summary = (
        alloc_df.assign(_SUBJECT=alloc_df['SUB_CODE'].astype(str).str.strip() +
                         (" - " + alloc_df['SUB_TITLE'].astype(str).str.strip()).where(alloc_df['SUB_TITLE'].astype(str).str.strip() != '', ""))
                 .groupby(['SUB_CODE', 'SUB_TITLE'], dropna=False)
                 .agg(TOTAL_STUDENTS=('REG_NO', 'count'),
                      HALLS_USED=('_HALL_KEY', pd.Series.nunique))
                 .reset_index()
                 .sort_values(['SUB_CODE', 'SUB_TITLE'])
    )

    with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
        alloc_cols = ['HALL_NO', 'SEAT_NO', 'REG_NO', 'NAME', 'SUB_CODE', 'SUB_TITLE', 'CLASS', 'DEPT', 'DATE', 'SESS']
        alloc_df[alloc_cols].to_excel(writer, index=False, sheet_name='Allocation')
        summary_cols = ['SUB_CODE', 'SUB_TITLE', 'TOTAL_STUDENTS', 'HALLS_USED']
        summary[summary_cols].to_excel(writer, index=False, sheet_name='Summary')

    return filename


# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', default_capacity=30)


@app.route('/allocate', methods=['POST'])
def allocate():
    if 'file' not in request.files:
        flash('No file part in the request', 'danger')
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'warning')
        return redirect(url_for('index'))

    if not allowed_file(file.filename):
        flash('Unsupported file format. Please upload CSV or Excel.', 'danger')
        return redirect(url_for('index'))

    # Capacity
    try:
        capacity = int(request.form.get('capacity', 30))
        if capacity <= 0:
            capacity = 30
    except Exception:
        capacity = 30

    # Save upload
    safe_name = secure_filename(file.filename)
    unique_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{safe_name}"
    upload_path = os.path.join(UPLOAD_FOLDER, unique_name)
    file.save(upload_path)

    # Read with pandas
    ext = safe_name.rsplit('.', 1)[1].lower()
    try:
        if ext == 'csv':
            raw = pd.read_csv(upload_path, dtype=str)
        else:
            raw = pd.read_excel(upload_path, dtype=str)
    except Exception as e:
        flash(f'Failed to read file: {e}', 'danger')
        return redirect(url_for('index'))

    try:
        norm = normalize_columns(raw)
    except Exception as e:
        flash(f'Column error: {e}', 'danger')
        return redirect(url_for('index'))

    # Allocate
    alloc_df = allocate_seats(norm, hall_capacity=capacity)

    # Save Excel
    download_filename = generate_excel(alloc_df)

    # Prepare preview and summary for UI
    preview_cols = ['HALL_NO', 'SEAT_NO', 'REG_NO', 'NAME', 'SUB_CODE', 'SUB_TITLE', 'CLASS', 'DEPT', 'DATE', 'SESS']
    preview_df = alloc_df[preview_cols].head(200)
    preview_records = preview_df.to_dict(orient='records')

    summary_df = (
        alloc_df.groupby(['SUB_CODE', 'SUB_TITLE'], dropna=False)
                .agg(TOTAL_STUDENTS=('REG_NO', 'count'), HALLS_USED=('_HALL_KEY', pd.Series.nunique))
                .reset_index()
                .sort_values(['SUB_CODE', 'SUB_TITLE'])
    )
    summary_records = summary_df.to_dict(orient='records')

    return render_template(
        'result.html',
        columns=preview_df.columns.tolist(),
        rows=preview_records,
        summary_columns=['SUB_CODE', 'SUB_TITLE', 'TOTAL_STUDENTS', 'HALLS_USED'],
        summary_rows=summary_records,
        download_filename=download_filename,
        capacity=capacity
    )


@app.route('/download/<path:filename>', methods=['GET'])
def download(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)


if __name__ == '__main__':
    # Run standalone
    app.run(host='127.0.0.1', port=5001, debug=True)
