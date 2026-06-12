"""
Cyient Foundation CRM Dashboard - Flask backend
================================================
A single-file Flask app exposing a JSON REST API for all modules,
a /api/dashboard endpoint for the Master Board, plus authentication
and role-scoped portals for Students, Trainers and Super Admins.

Run: python app.py
"""
import os
import uuid
import functools
from datetime import datetime
from flask import (Flask, jsonify, request, render_template, abort,
                   session, redirect, url_for, send_from_directory)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database import get_db, close_db, init_db, rows_to_dicts, row_to_dict


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
app = Flask(__name__, instance_relative_config=True)
app.config["JSON_SORT_KEYS"] = False
app.config["SECRET_KEY"] = "cyient-foundation-crm-prototype-secret-key-change-in-prod"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB max upload (small PDFs/videos)
app.teardown_appcontext(close_db)

UPLOAD_DIR = os.path.join(app.instance_path, "uploads")
ALLOWED_EXT = {"pdf", "mp4", "webm", "mov", "png", "jpg", "jpeg", "ppt", "pptx", "doc", "docx"}
DEFAULT_PASSWORD = "cyient@123"

with app.app_context():
    init_db(app)

# Ensure the uploads folder exists and drop in one sample PDF so seeded
# chapter-file rows have something real to download.
os.makedirs(UPLOAD_DIR, exist_ok=True)
_sample_pdf = os.path.join(UPLOAD_DIR, "sample_chapter_material.pdf")
if not os.path.exists(_sample_pdf):
    # A minimal but valid one-page PDF.
    _pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
        b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>endobj\n"
        b"4 0 obj<</Length 90>>stream\n"
        b"BT /F1 22 Tf 70 700 Td (Cyient Foundation) Tj "
        b"0 -34 Td /F1 14 Tf (Sample Chapter Material) Tj ET\n"
        b"endstream endobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n"
        b"0000000052 00000 n \n0000000101 00000 n \n0000000229 00000 n \n"
        b"0000000370 00000 n \ntrailer<</Size 6/Root 1 0 R>>\n"
        b"startxref\n443\n%%EOF"
    )
    with open(_sample_pdf, "wb") as f:
        f.write(_pdf_bytes)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def current_user():
    """Return the logged-in user row (dict) or None."""
    uid = session.get("user_id")
    if not uid:
        return None
    return fetch_one("SELECT * FROM users WHERE id = ?", (uid,))


def require_role(*roles):
    """Decorator for API endpoints: ensure a logged-in user with an allowed role."""
    def wrapper(fn):
        @functools.wraps(fn)
        def inner(*args, **kwargs):
            u = current_user()
            if not u:
                return jsonify({"error": "not authenticated"}), 401
            if roles and u["role"] not in roles:
                return jsonify({"error": "forbidden"}), 403
            return fn(*args, **kwargs)
        return inner
    return wrapper


def provision_user(role, ref_id, email, name):
    """Create a login user for a newly added student/trainer/administrator."""
    if not email:
        return
    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE username = ?", (email,)).fetchone()
    if existing:
        return
    db.execute(
        "INSERT INTO users (username,password_hash,role,ref_id,display_name,must_change_password) "
        "VALUES (?,?,?,?,?,?)",
        (email, generate_password_hash(DEFAULT_PASSWORD), role, ref_id, name, 1),
    )
    db.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def fetch_all(query, params=()):
    db = get_db()
    return rows_to_dicts(db.execute(query, params).fetchall())


def fetch_one(query, params=()):
    db = get_db()
    return row_to_dict(db.execute(query, params).fetchone())


def execute(query, params=()):
    db = get_db()
    cur = db.execute(query, params)
    db.commit()
    return cur           # executing the database


def json_body():
    """Get JSON body or empty dict. Handles missing Content-Type gracefully."""
    return request.get_json(silent=True) or {}


# Registry of all CRUD entities, populated by build_crud(). Used by the bulk
# upload feature to know each entity's table, insertable columns, and the
# hook that provisions login users for people-type entities.
ENTITY_REGISTRY = {}


def build_crud(name, table, fields, *, search_fields=None, select_extra="", joins="", after_create=None):
    """Register a standard set of CRUD endpoints under /api/<name>.

    fields        -> list of column names that can be inserted/updated
    search_fields -> columns that participate in a free-text ?q= search
    select_extra  -> extra SELECT columns (joined data) appended after "<table>.*"
    joins         -> raw SQL JOIN string appended after FROM clause
    after_create  -> optional callback(new_id, body) run after a successful insert
    """
    search_fields = search_fields or []
    ENTITY_REGISTRY[name] = {"table": table, "fields": fields, "after_create": after_create}
    base_select = f"SELECT {table}.*{(', ' + select_extra) if select_extra else ''} FROM {table} {joins}"

    @app.route(f"/api/{name}", methods=["GET"], endpoint=f"list_{name}")
    def list_items():
        q = request.args.get("q", "").strip()
        params = []
        where = ""
        if q and search_fields:
            # If a field already contains a dot, use it verbatim;
            # otherwise prefix with the base table so we don't get
            # ambiguous column errors after joins.
            def _qual(f):
                return f if "." in f else f"{table}.{f}"
            clauses = " OR ".join([f"{_qual(f)} LIKE ?" for f in search_fields])
            where = f"WHERE {clauses}"
            params = [f"%{q}%"] * len(search_fields)
        order = f" ORDER BY {table}.id DESC"
        return jsonify(fetch_all(base_select + " " + where + order, params))

    @app.route(f"/api/{name}/<int:item_id>", methods=["GET"], endpoint=f"get_{name}")
    def get_item(item_id):
        row = fetch_one(base_select + f" WHERE {table}.id = ?", (item_id,))
        if not row:
            abort(404, description=f"{name} not found")
        return jsonify(row)

    @app.route(f"/api/{name}", methods=["POST"], endpoint=f"create_{name}")
    def create_item():
        body = json_body()
        cols, vals = [], []
        for f in fields:
            if f in body:
                cols.append(f)
                vals.append(body[f])
        if not cols:
            return jsonify({"error": "no fields supplied"}), 400
        placeholders = ",".join(["?"] * len(cols))
        try:
            cur = execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})", vals)
        except Exception as e:
            return jsonify({"error": str(e)}), 400
        new_id = cur.lastrowid
        if after_create:
            try:
                after_create(new_id, body)
            except Exception as e:
                print(f"[after_create:{name}] {e}")
        row = fetch_one(base_select + f" WHERE {table}.id = ?", (new_id,))
        return jsonify(row), 201

    @app.route(f"/api/{name}/<int:item_id>", methods=["PUT"], endpoint=f"update_{name}")
    def update_item(item_id):
        body = json_body()
        cols, vals = [], []
        for f in fields:
            if f in body:
                cols.append(f"{f} = ?")
                vals.append(body[f])
        if not cols:
            return jsonify({"error": "no fields supplied"}), 400
        vals.append(item_id)
        try:
            execute(f"UPDATE {table} SET {','.join(cols)} WHERE id = ?", vals)
        except Exception as e:
            return jsonify({"error": str(e)}), 400
        row = fetch_one(base_select + f" WHERE {table}.id = ?", (item_id,))
        if not row:
            abort(404, description=f"{name} not found")
        return jsonify(row)

    @app.route(f"/api/{name}/<int:item_id>", methods=["DELETE"], endpoint=f"delete_{name}")
    def delete_item(item_id):
        execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
        return jsonify({"deleted": True, "id": item_id})


# ---------------------------------------------------------------------------
# CRUD registrations for each module.
# ---------------------------------------------------------------------------
build_crud(
    "administrators", "administrators",
    fields=["name", "email", "role", "permissions", "phone", "status"],
    search_fields=["name", "email", "role"],
    after_create=lambda nid, body: provision_user("superadmin", nid, body.get("email"), body.get("name")),
)

build_crud(
    "projects", "projects",
    fields=["name", "description", "institution", "start_date", "end_date",
            "status", "progress", "budget"],
    search_fields=["name", "institution", "status"],
)

build_crud(
    "courses", "courses",
    fields=["name", "project_id", "duration_weeks", "objectives",
            "learning_outcomes", "target_group", "status"],
    search_fields=["courses.name", "target_group", "courses.status"],
    select_extra="projects.name AS project_name",
    joins="LEFT JOIN projects ON courses.project_id = projects.id",
)

build_crud(
    "modules", "modules",
    fields=["name", "course_id", "learning_goals", "sequence", "duration_hours"],
    search_fields=["modules.name", "learning_goals"],
    select_extra="courses.name AS course_name",
    joins="LEFT JOIN courses ON modules.course_id = courses.id",
)

build_crud(
    "chapters", "chapters",
    fields=["name", "module_id", "content_type", "sequence", "description"],
    search_fields=["chapters.name", "content_type"],
    select_extra="modules.name AS module_name",
    joins="LEFT JOIN modules ON chapters.module_id = modules.id",
)

build_crud(
    "skills", "skills",
    fields=["name", "description", "category", "max_grade"],
    search_fields=["name", "category"],
)

build_crud(
    "trainers", "trainers",
    fields=["name", "email", "phone", "specialization", "qualification",
            "experience_years", "status", "joined_date"],
    search_fields=["name", "email", "specialization", "status"],
    after_create=lambda nid, body: provision_user("trainer", nid, body.get("email"), body.get("name")),
)

build_crud(
    "students", "students",
    fields=["name", "email", "phone", "project_id", "course_id", "batch",
            "enrollment_date", "status", "gender", "institution"],
    search_fields=["students.name", "students.email", "batch", "institution"],
    select_extra="projects.name AS project_name, courses.name AS course_name",
    joins="LEFT JOIN projects ON students.project_id = projects.id "
          "LEFT JOIN courses ON students.course_id = courses.id",
    after_create=lambda nid, body: provision_user("student", nid, body.get("email"), body.get("name")),
)

build_crud(
    "chapter_assignments", "chapter_assignments",
    fields=["chapter_id", "trainer_id", "batch", "scheduled_date", "status", "notes"],
    search_fields=["batch", "chapter_assignments.status"],
    select_extra="chapters.name AS chapter_name, trainers.name AS trainer_name",
    joins="LEFT JOIN chapters ON chapter_assignments.chapter_id = chapters.id "
          "LEFT JOIN trainers ON chapter_assignments.trainer_id = trainers.id",
)

build_crud(
    "activities", "activities",
    fields=["name", "activity_type", "project_id", "activity_date",
            "description", "participants_count", "location"],
    search_fields=["activities.name", "activity_type", "location"],
    select_extra="projects.name AS project_name",
    joins="LEFT JOIN projects ON activities.project_id = projects.id",
)

build_crud(
    "student_attendance", "student_attendance",
    fields=["student_id", "course_id", "attendance_date", "session", "status", "remarks"],
    search_fields=["student_attendance.status", "session"],
    select_extra="students.name AS student_name, courses.name AS course_name",
    joins="LEFT JOIN students ON student_attendance.student_id = students.id "
          "LEFT JOIN courses ON student_attendance.course_id = courses.id",
)

build_crud(
    "trainer_attendance", "trainer_attendance",
    fields=["trainer_id", "attendance_date", "hours_taught", "status", "remarks"],
    search_fields=["trainer_attendance.status"],
    select_extra="trainers.name AS trainer_name",
    joins="LEFT JOIN trainers ON trainer_attendance.trainer_id = trainers.id",
)

build_crud(
    "student_skills", "student_skills",
    fields=["student_id", "skill_id", "grade", "skill_level", "evaluated_on", "remarks"],
    search_fields=["skill_level"],
    select_extra="students.name AS student_name, skills.name AS skill_name",
    joins="LEFT JOIN students ON student_skills.student_id = students.id "
          "LEFT JOIN skills ON student_skills.skill_id = skills.id",
)

build_crud(
    "volunteers", "volunteers",
    fields=["name", "email", "phone", "organization", "expertise",
            "area_of_interest", "availability", "activity_id",
            "hours_contributed", "joined_date", "status", "notes"],
    search_fields=["volunteers.name", "email", "organization", "expertise", "area_of_interest"],
    select_extra="activities.name AS activity_name",
    joins="LEFT JOIN activities ON volunteers.activity_id = activities.id",
)

build_crud(
    "internships", "internships",
    fields=["student_id", "company_name", "role", "start_date", "end_date", "status", "payment_type", "stipend",
            "visitor_card_id", "reporting_manager", "offer_letter_file", "internship_report_file",
            "certificate_file", "lor_file"],
    search_fields=["company_name", "role", "internships.status", "visitor_card_id", "students.name", "students.institution", "students.email", "students.phone"],
    select_extra="students.name AS student_name, students.institution AS institution, students.email AS email, students.phone AS phone",
    joins="LEFT JOIN students ON internships.student_id = students.id",
)

build_crud(
    "feedbacks", "feedbacks",
    fields=["provider_name", "provider_role", "subject", "comments", "rating", "status"],
    search_fields=["provider_name", "provider_role", "subject", "status"],
)

build_crud(
    "tickets", "tickets",
    fields=["raised_by_user_id", "raised_by_name", "raised_by_role", "subject",
            "description", "category", "priority", "status", "response"],
    search_fields=["subject", "raised_by_name", "raised_by_role", "tickets.status", "priority"],
)

build_crud(
    "certificates", "certificates",
    fields=["student_id", "course_id", "certificate_no", "grade", "issued_date", "status"],
    search_fields=["certificate_no", "certificates.status"],
    select_extra="students.name AS student_name, courses.name AS course_name",
    joins="LEFT JOIN students ON certificates.student_id = students.id "
          "LEFT JOIN courses ON certificates.course_id = courses.id",
)


# ---------------------------------------------------------------------------
# Master board / dashboard aggregates
# ---------------------------------------------------------------------------
@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    """Aggregate counters, project status breakdown and recent attendance trend."""
    db = get_db()

    row = db.execute("""
        SELECT 
            (SELECT COUNT(*) FROM projects),
            (SELECT COUNT(*) FROM projects WHERE status='Active'),
            (SELECT COUNT(*) FROM courses),
            (SELECT COUNT(*) FROM modules),
            (SELECT COUNT(*) FROM chapters),
            (SELECT COUNT(*) FROM students),
            (SELECT COUNT(*) FROM students WHERE status='Active'),
            (SELECT COUNT(*) FROM trainers),
            (SELECT COUNT(*) FROM trainers WHERE status='Active'),
            (SELECT COUNT(*) FROM administrators),
            (SELECT COUNT(*) FROM skills),
            (SELECT COUNT(*) FROM activities),
            (SELECT COUNT(*) FROM chapter_assignments),
            (SELECT COUNT(*) FROM volunteers),
            (SELECT COUNT(*) FROM volunteers WHERE status='Active'),
            (SELECT COUNT(*) FROM internships),
            (SELECT COUNT(*) FROM feedbacks),
            (SELECT COUNT(*) FROM tickets),
            (SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress')),
            (SELECT COUNT(*) FROM certificates)
    """).fetchone()

    counts = {
        "projects": row[0],
        "active_projects": row[1],
        "courses": row[2],
        "modules": row[3],
        "chapters": row[4],
        "students": row[5],
        "active_students": row[6],
        "trainers": row[7],
        "active_trainers": row[8],
        "administrators": row[9],
        "skills": row[10],
        "activities": row[11],
        "chapter_assignments": row[12],
        "volunteers": row[13],
        "active_volunteers": row[14],
        "internships": row[15],
        "feedbacks": row[16],
        "tickets": row[17],
        "open_tickets": row[18],
        "certificates": row[19],
    }

    # ----- Project status breakdown -----
    project_status = rows_to_dicts(db.execute(
        "SELECT status, COUNT(*) AS count FROM projects GROUP BY status"
    ).fetchall())

    # ----- Top projects by progress -----
    top_projects = rows_to_dicts(db.execute(
        "SELECT id, name, status, progress FROM projects ORDER BY progress DESC LIMIT 5"
    ).fetchall())

    # ----- Attendance: present % per day (last 14 days) -----
    attendance_trend = rows_to_dicts(db.execute("""
        SELECT attendance_date,
               COUNT(*) AS total,
               SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) AS present_count
        FROM student_attendance
        GROUP BY attendance_date
        ORDER BY attendance_date DESC
        LIMIT 14
    """).fetchall())
    attendance_trend = list(reversed(attendance_trend))
    for r in attendance_trend:
        r["present_pct"] = round((r["present_count"] / r["total"]) * 100, 1) if r["total"] else 0

    # ----- Students by status -----
    students_by_status = rows_to_dicts(db.execute(
        "SELECT status, COUNT(*) AS count FROM students GROUP BY status"
    ).fetchall())

    # ----- Course-wise student count -----
    course_student_count = rows_to_dicts(db.execute("""
        SELECT c.name AS course_name, COUNT(s.id) AS student_count
        FROM courses c LEFT JOIN students s ON s.course_id = c.id
        GROUP BY c.id ORDER BY student_count DESC LIMIT 7
    """).fetchall())

    # ----- Recent activities -----
    recent_activities = rows_to_dicts(db.execute("""
        SELECT a.id, a.name, a.activity_type, a.activity_date, a.participants_count,
               p.name AS project_name
        FROM activities a LEFT JOIN projects p ON a.project_id = p.id
        ORDER BY a.activity_date DESC LIMIT 6
    """).fetchall())

    return jsonify({
        "counts": counts,
        "project_status": project_status,
        "top_projects": top_projects,
        "attendance_trend": attendance_trend,
        "students_by_status": students_by_status,
        "course_student_count": course_student_count,
        "recent_activities": recent_activities,
    })


# ---------------------------------------------------------------------------
# Helper: lightweight option lists for dropdowns
# ---------------------------------------------------------------------------
@app.route("/api/options/<entity>", methods=["GET"])
def options(entity):
    """Return [{id, name}] pairs for selects. Used to populate FK dropdowns."""
    allowed = {
        "projects": "SELECT id, name FROM projects ORDER BY name",
        "courses": "SELECT id, name FROM courses ORDER BY name",
        "modules": "SELECT id, name FROM modules ORDER BY name",
        "chapters": "SELECT id, name FROM chapters ORDER BY name",
        "trainers": "SELECT id, name FROM trainers ORDER BY name",
        "students": "SELECT id, name FROM students ORDER BY name",
        "skills": "SELECT id, name FROM skills ORDER BY name",
        "volunteers": "SELECT id, name FROM volunteers ORDER BY name",
        "activities": "SELECT id, name FROM activities ORDER BY name",
        "modules_all": "SELECT id, name FROM modules ORDER BY name",
    }
    if entity not in allowed:
        return jsonify({"error": "unknown entity"}), 400
    return jsonify(fetch_all(allowed[entity]))


# ---------------------------------------------------------------------------
# Frontend (single page) + error handlers
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    if not session.get("user_id") or session.get("role") != "superadmin":
        return redirect("/login")
    return render_template("index.html")

@app.route("/superadmin")
def superadmin_redirect():
    return redirect("/")

@app.route("/login")
def login_selection():
    return render_template("role_selection.html")

@app.route("/login/<role>")
def login_form(role):
    if role not in ["student", "trainer", "superadmin"]:
        abort(404)
    display_names = {"student": "Student", "trainer": "Trainer", "superadmin": "Super Admin"}
    return render_template("login.html", role=role, role_name=display_names[role])

@app.route("/student")
def student_dashboard():
    if not session.get("user_id") or session.get("role") != "student":
        return redirect("/login/student")
    name = session.get("name") or "Student"
    initials = "".join([p[0] for p in name.split()[:2]]).upper() or "S"
    return render_template("student.html", user_name=name, user_initials=initials)

@app.route("/trainer")
def trainer_dashboard():
    if not session.get("user_id") or session.get("role") != "trainer":
        return redirect("/login/trainer")
    name = session.get("name") or "Trainer"
    initials = "".join([p[0] for p in name.split()[:2]]).upper() or "T"
    return render_template("trainer.html", user_name=name, user_initials=initials)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    body = json_body()
    username = (body.get("username") or "").strip().lower()
    password = body.get("password") or ""
    role = (body.get("role") or "").strip()

    user = fetch_one("SELECT * FROM users WHERE lower(username) = ?", (username,))
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid username or password"}), 401
    if role and user["role"] != role:
        return jsonify({"error": f"This account is not a {role} account"}), 403

    session["user_id"] = user["id"]
    session["role"] = user["role"]
    session["name"] = user["display_name"]
    return jsonify({
        "id": user["id"], "username": user["username"], "role": user["role"],
        "name": user["display_name"], "ref_id": user["ref_id"],
        "must_change_password": user["must_change_password"],
    })


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    u = current_user()
    if not u:
        return jsonify({"error": "not authenticated"}), 401
    return jsonify({"id": u["id"], "username": u["username"], "role": u["role"],
                    "name": u["display_name"], "ref_id": u["ref_id"]})


@app.route("/api/auth/forgot", methods=["POST"])
def auth_forgot():
    """Prototype reset: verify the username exists then set a new password."""
    body = json_body()
    username = (body.get("username") or "").strip().lower()
    new_password = body.get("new_password") or ""
    role = (body.get("role") or "").strip()
    if len(new_password) < 4:
        return jsonify({"error": "Password must be at least 4 characters"}), 400
    user = fetch_one("SELECT * FROM users WHERE lower(username) = ?", (username,))
    if not user:
        return jsonify({"error": "No account found with that username"}), 404
    if role and user["role"] != role:
        return jsonify({"error": f"That username is not a {role} account"}), 403
    execute("UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?",
            (generate_password_hash(new_password), user["id"]))
    return jsonify({"ok": True, "message": "Password reset successful. You can now log in."})


@app.route("/api/auth/change-password", methods=["POST"])
def auth_change_password():
    u = current_user()
    if not u:
        return jsonify({"error": "not authenticated"}), 401
    body = json_body()
    current_pw = body.get("current_password") or ""
    new_pw = body.get("new_password") or ""
    if not check_password_hash(u["password_hash"], current_pw):
        return jsonify({"error": "Current password is incorrect"}), 400
    if len(new_pw) < 4:
        return jsonify({"error": "New password must be at least 4 characters"}), 400
    execute("UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?",
            (generate_password_hash(new_pw), u["id"]))
    return jsonify({"ok": True, "message": "Password updated successfully"})


# ---------------------------------------------------------------------------
# Shared: tickets & feedback raised by the logged-in user
# ---------------------------------------------------------------------------
@app.route("/api/me/tickets", methods=["GET", "POST"])
def me_tickets():
    u = current_user()
    if not u:
        return jsonify({"error": "not authenticated"}), 401
    if request.method == "POST":
        b = json_body()
        execute(
            "INSERT INTO tickets (raised_by_user_id,raised_by_name,raised_by_role,subject,description,category,priority,status) "
            "VALUES (?,?,?,?,?,?,?, 'Open')",
            (u["id"], u["display_name"], u["role"], b.get("subject"), b.get("description"),
             b.get("category", "General"), b.get("priority", "Medium")),
        )
        return jsonify({"ok": True}), 201
    rows = fetch_all("SELECT * FROM tickets WHERE raised_by_user_id = ? ORDER BY id DESC", (u["id"],))
    return jsonify(rows)


@app.route("/api/me/tickets/<int:item_id>", methods=["PUT", "DELETE"])
def me_tickets_item(item_id):
    u = current_user()
    if not u:
        return jsonify({"error": "not authenticated"}), 401
    
    # Verify ownership
    ticket = fetch_one("SELECT * FROM tickets WHERE id = ? AND raised_by_user_id = ?", (item_id, u["id"]))
    if not ticket:
        abort(404, description="Ticket not found or unauthorized")

    if request.method == "DELETE":
        execute("DELETE FROM tickets WHERE id = ?", (item_id,))
        return jsonify({"ok": True})
    
    # PUT
    b = json_body()
    execute(
        "UPDATE tickets SET subject = ?, category = ?, priority = ?, description = ?, updated_at = datetime('now') WHERE id = ?",
        (b.get("subject", ticket["subject"]), b.get("category", ticket["category"]), b.get("priority", ticket["priority"]), b.get("description", ticket["description"]), item_id)
    )
    return jsonify({"ok": True})


@app.route("/api/me/feedback", methods=["GET", "POST"])
def me_feedback():
    u = current_user()
    if not u:
        return jsonify({"error": "not authenticated"}), 401
    role_name = "Student" if u["role"] == "student" else "Trainer" if u["role"] == "trainer" else "Admin"
    if request.method == "POST":
        b = json_body()
        execute(
            "INSERT INTO feedbacks (provider_name,provider_role,subject,comments,rating,status) "
            "VALUES (?,?,?,?,?, 'Pending')",
            (u["display_name"], role_name, b.get("subject"), b.get("comments"), b.get("rating", 5)),
        )
        return jsonify({"ok": True}), 201
    rows = fetch_all("SELECT * FROM feedbacks WHERE provider_name = ? ORDER BY id DESC", (u["display_name"],))
    return jsonify(rows)


@app.route("/api/me/feedback/<int:item_id>", methods=["PUT", "DELETE"])
def me_feedback_item(item_id):
    u = current_user()
    if not u:
        return jsonify({"error": "not authenticated"}), 401
    
    # Verify ownership
    feedback = fetch_one("SELECT * FROM feedbacks WHERE id = ? AND provider_name = ?", (item_id, u["display_name"]))
    if not feedback:
        abort(404, description="Feedback not found or unauthorized")

    if request.method == "DELETE":
        execute("DELETE FROM feedbacks WHERE id = ?", (item_id,))
        return jsonify({"ok": True})
    
    # PUT
    b = json_body()
    execute(
        "UPDATE feedbacks SET subject = ?, comments = ?, rating = ? WHERE id = ?",
        (b.get("subject", feedback["subject"]), b.get("comments", feedback["comments"]), b.get("rating", feedback["rating"]), item_id)
    )
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# STUDENT portal data
# ---------------------------------------------------------------------------
@app.route("/api/student/summary", methods=["GET"])
@require_role("student")
def student_summary():
    u = current_user()
    sid = u["ref_id"]
    student = fetch_one("SELECT s.*, c.name AS course_name, p.name AS project_name "
                        "FROM students s LEFT JOIN courses c ON s.course_id=c.id "
                        "LEFT JOIN projects p ON s.project_id=p.id WHERE s.id = ?", (sid,))
    att = fetch_one("""SELECT COUNT(*) AS total,
                       SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) AS present
                       FROM student_attendance WHERE student_id = ?""", (sid,))
    total = att["total"] or 0
    present = att["present"] or 0
    chap = fetch_one("""SELECT
                        SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) AS completed,
                        SUM(CASE WHEN status='In Progress' THEN 1 ELSE 0 END) AS in_progress,
                        COUNT(*) AS tracked
                        FROM student_chapter_status WHERE student_id = ?""", (sid,))
    total_chapters = fetch_one("SELECT COUNT(*) AS n FROM chapters")["n"]
    certs = fetch_one("SELECT COUNT(*) AS n FROM certificates WHERE student_id = ?", (sid,))["n"]
    tickets = fetch_one("SELECT COUNT(*) AS n FROM tickets WHERE raised_by_user_id = ?", (u["id"],))["n"]
    recent_att = fetch_all("""SELECT sa.attendance_date, sa.session, sa.status, c.name AS course_name
                              FROM student_attendance sa LEFT JOIN courses c ON sa.course_id=c.id
                              WHERE sa.student_id = ? ORDER BY date(sa.attendance_date) DESC LIMIT 8""", (sid,))
    return jsonify({
        "student": student,
        "attendance": {"total": total, "present": present,
                       "pct": round((present/total)*100, 1) if total else 0},
        "chapters": {"completed": chap["completed"] or 0,
                     "in_progress": chap["in_progress"] or 0,
                     "total": total_chapters},
        "certificates": certs,
        "tickets": tickets,
        "recent_attendance": recent_att,
    })


@app.route("/api/student/chapters", methods=["GET"])
@require_role("student")
def student_chapters():
    u = current_user()
    sid = u["ref_id"]
    rows = fetch_all("""
        SELECT ch.id AS chapter_id, ch.name AS chapter_name, ch.content_type,
               m.name AS module_name, co.name AS course_name,
               COALESCE(scs.status, 'Not Started') AS status,
               (SELECT COUNT(*) FROM chapter_files cf WHERE cf.chapter_id = ch.id) AS file_count
        FROM chapters ch
        LEFT JOIN modules m ON ch.module_id = m.id
        LEFT JOIN courses co ON m.course_id = co.id
        LEFT JOIN student_chapter_status scs ON scs.chapter_id = ch.id AND scs.student_id = ?
        ORDER BY co.name, m.sequence, ch.sequence
    """, (sid,))
    return jsonify(rows)


@app.route("/api/student/chapter-status", methods=["POST"])
@require_role("student")
def student_set_chapter_status():
    u = current_user()
    sid = u["ref_id"]
    b = json_body()
    cid = b.get("chapter_id")
    status = b.get("status", "In Progress")
    execute("""INSERT INTO student_chapter_status (student_id, chapter_id, status, updated_at)
               VALUES (?,?,?, datetime('now'))
               ON CONFLICT(student_id, chapter_id)
               DO UPDATE SET status = excluded.status, updated_at = datetime('now')""",
            (sid, cid, status))
    return jsonify({"ok": True})


@app.route("/api/student/attendance", methods=["GET"])
@require_role("student")
def student_attendance_list():
    u = current_user()
    rows = fetch_all("""SELECT sa.*, c.name AS course_name
                        FROM student_attendance sa LEFT JOIN courses c ON sa.course_id=c.id
                        WHERE sa.student_id = ? ORDER BY date(sa.attendance_date) DESC""", (u["ref_id"],))
    return jsonify(rows)


@app.route("/api/student/certificates", methods=["GET"])
@require_role("student")
def student_certificates():
    u = current_user()
    rows = fetch_all("""SELECT ce.*, c.name AS course_name
                        FROM certificates ce LEFT JOIN courses c ON ce.course_id=c.id
                        WHERE ce.student_id = ? ORDER BY ce.id DESC""", (u["ref_id"],))
    return jsonify(rows)


@app.route("/api/student/certificates/<int:cert_id>/download", methods=["GET"])
@require_role("student")
def download_student_certificate(cert_id):
    """Generate and download a certificate as PDF."""
    u = current_user()
    cert = fetch_one("""SELECT ce.*, c.name AS course_name, s.name AS student_name
                        FROM certificates ce 
                        LEFT JOIN courses c ON ce.course_id = c.id
                        LEFT JOIN students s ON ce.student_id = s.id
                        WHERE ce.id = ? AND ce.student_id = ?""", 
                     (cert_id, u["ref_id"]))
    if not cert:
        abort(404, description="Certificate not found or unauthorized")
    
    # Generate a simple PDF certificate
    student_name = cert["student_name"] or "Student"
    course_name = cert["course_name"] or "Course"
    cert_no = cert["certificate_no"] or f"CERT-{cert_id}"
    grade = cert["grade"] or "N/A"
    issued_date = cert["issued_date"] or "N/A"
    
    # Create a basic PDF certificate
    pdf_content = generate_certificate_pdf(student_name, course_name, cert_no, grade, issued_date)
    
    filename = f"Certificate_{cert_no}.pdf"
    from flask import Response
    return Response(
        pdf_content,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


def generate_certificate_pdf(student_name, course_name, cert_no, grade, issued_date):
    """Generate a simple PDF certificate."""
    # Minimal but valid PDF structure for a certificate
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 792 612]"
        b"/Resources<</Font<</F1 4 0 R/F2 5 0 R>>>>/Contents 6 0 R>>endobj\n"
        b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica-Bold>>endobj\n"
    )
    
    # Prepare the certificate content
    student_line = f"({student_name})"
    course_line = f"({course_name})"
    cert_no_line = f"({cert_no})"
    grade_line = f"({grade})"
    date_line = f"({issued_date})"
    
    content = (
        b"BT\n"
        b"/F2 32 Tf 150 520 Td (CYIENT FOUNDATION) Tj\n"
        b"0 -40 Td /F1 18 Tf (Certificate of Completion) Tj\n"
        b"0 -50 Td /F1 12 Tf (This is proudly presented to) Tj\n"
        b"0 -35 Td /F2 24 Tf " + student_line.encode() + b" Tj\n"
        b"0 -45 Td /F1 12 Tf (for successfully completing the course) Tj\n"
        b"0 -35 Td /F2 16 Tf " + course_line.encode() + b" Tj\n"
        b"0 -80 Td /F1 10 Tf (Certificate Number: ) Tj\n"
        b"140 0 Td " + cert_no_line.encode() + b" Tj\n"
        b"-140 -20 Td (Grade: ) Tj\n"
        b"50 0 Td " + grade_line.encode() + b" Tj\n"
        b"-50 -20 Td (Issued: ) Tj\n"
        b"50 0 Td " + date_line.encode() + b" Tj\n"
        b"ET\n"
    )
    
    content_length = len(content)
    pdf_bytes += (
        b"6 0 obj<</Length " + str(content_length).encode() + b">>stream\n"
    ) + content + (
        b"\nendstream endobj\n"
        b"xref\n0 7\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000052 00000 n \n"
        b"0000000101 00000 n \n"
        b"0000000247 00000 n \n"
        b"0000000320 00000 n \n"
    )
    
    xref_offset = len(pdf_bytes)
    pdf_bytes += (
        b"0000000394 00000 n \n"
        b"trailer<</Size 7/Root 1 0 R>>\n"
        b"startxref\n" + str(xref_offset).encode() + b"\n%%EOF"
    )
    
    return pdf_bytes


# ---------------------------------------------------------------------------
# TRAINER portal data
# ---------------------------------------------------------------------------
@app.route("/api/trainer/summary", methods=["GET"])
@require_role("trainer")
def trainer_summary():
    u = current_user()
    tid = u["ref_id"]
    trainer = fetch_one("SELECT * FROM trainers WHERE id = ?", (tid,))
    att = fetch_one("""SELECT COUNT(*) AS total,
                       SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) AS present,
                       SUM(hours_taught) AS hours
                       FROM trainer_attendance WHERE trainer_id = ?""", (tid,))
    total = att["total"] or 0
    present = att["present"] or 0
    assigns = fetch_one("""SELECT COUNT(*) AS total,
                           SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) AS completed
                           FROM chapter_assignments WHERE trainer_id = ?""", (tid,))
    students_total = fetch_one("SELECT COUNT(*) AS n FROM students")["n"]
    active_students = fetch_one("SELECT COUNT(*) AS n FROM students WHERE status='Active'")["n"]
    certs = fetch_one("SELECT COUNT(*) AS n FROM certificates")["n"]
    recent_att = fetch_all("""SELECT attendance_date, status, hours_taught
                              FROM trainer_attendance WHERE trainer_id = ?
                              ORDER BY date(attendance_date) DESC LIMIT 8""", (tid,))
    return jsonify({
        "trainer": trainer,
        "attendance": {"total": total, "present": present,
                       "pct": round((present/total)*100, 1) if total else 0,
                       "hours": att["hours"] or 0},
        "chapters": {"total": assigns["total"] or 0, "completed": assigns["completed"] or 0},
        "students": {"total": students_total, "active": active_students},
        "certificates": certs,
        "recent_attendance": recent_att,
    })


@app.route("/api/trainer/chapters", methods=["GET"])
@require_role("trainer")
def trainer_chapters():
    u = current_user()
    tid = u["ref_id"]
    rows = fetch_all("""
        SELECT DISTINCT ch.id AS chapter_id, ch.name AS chapter_name, ch.content_type,
               m.name AS module_name, co.name AS course_name,
               ca.batch, ca.status AS assignment_status, ca.id AS assignment_id,
               (SELECT COUNT(*) FROM chapter_files cf WHERE cf.chapter_id = ch.id) AS file_count
        FROM chapter_assignments ca
        JOIN chapters ch ON ca.chapter_id = ch.id
        LEFT JOIN modules m ON ch.module_id = m.id
        LEFT JOIN courses co ON m.course_id = co.id
        WHERE ca.trainer_id = ?
        ORDER BY co.name, m.sequence, ch.sequence
    """, (tid,))
    return jsonify(rows)


@app.route("/api/trainer/assignment-status", methods=["POST"])
@require_role("trainer")
def trainer_assignment_status():
    b = json_body()
    execute("UPDATE chapter_assignments SET status = ? WHERE id = ?",
            (b.get("status"), b.get("assignment_id")))
    return jsonify({"ok": True})


@app.route("/api/trainer/certificates", methods=["GET"])
@require_role("trainer")
def trainer_certificates():
    rows = fetch_all("""SELECT ce.*, s.name AS student_name, c.name AS course_name
                        FROM certificates ce
                        LEFT JOIN students s ON ce.student_id = s.id
                        LEFT JOIN courses c ON ce.course_id = c.id
                        ORDER BY ce.id DESC""")
    return jsonify(rows)


@app.route("/api/trainer/certificates/<int:cert_id>/download", methods=["GET"])
@require_role("trainer")
def download_trainer_certificate(cert_id):
    """Generate and download a student's certificate as PDF (trainer view)."""
    cert = fetch_one("""SELECT ce.*, c.name AS course_name, s.name AS student_name
                        FROM certificates ce 
                        LEFT JOIN courses c ON ce.course_id = c.id
                        LEFT JOIN students s ON ce.student_id = s.id
                        WHERE ce.id = ?""", (cert_id,))
    if not cert:
        abort(404, description="Certificate not found")
    
    # Generate a simple PDF certificate
    student_name = cert["student_name"] or "Student"
    course_name = cert["course_name"] or "Course"
    cert_no = cert["certificate_no"] or f"CERT-{cert_id}"
    grade = cert["grade"] or "N/A"
    issued_date = cert["issued_date"] or "N/A"
    
    # Create a basic PDF certificate
    pdf_content = generate_certificate_pdf(student_name, course_name, cert_no, grade, issued_date)
    
    filename = f"Certificate_{cert_no}.pdf"
    from flask import Response
    return Response(
        pdf_content,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ---------------------------------------------------------------------------
# Chapter files: list / upload / download  (shared by student + trainer)
# ---------------------------------------------------------------------------
@app.route("/api/chapters/<int:chapter_id>/files", methods=["GET"])
def chapter_files_list(chapter_id):
    rows = fetch_all("SELECT * FROM chapter_files WHERE chapter_id = ? ORDER BY id DESC", (chapter_id,))
    return jsonify(rows)


@app.route("/api/chapters/<int:chapter_id>/files", methods=["POST"])
@require_role("trainer", "superadmin")
def chapter_files_upload(chapter_id):
    u = current_user()
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    f = request.files["file"]
    if not f or f.filename == "":
        return jsonify({"error": "No file selected"}), 400
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in ALLOWED_EXT:
        return jsonify({"error": f"File type .{ext} not allowed"}), 400
    stored = f"{uuid.uuid4().hex}.{ext}"
    safe_original = secure_filename(f.filename)
    path = os.path.join(UPLOAD_DIR, stored)
    f.save(path)
    size = os.path.getsize(path)
    ftype = "pdf" if ext == "pdf" else "video" if ext in ("mp4", "webm", "mov") else "other"
    execute("""INSERT INTO chapter_files
               (chapter_id,stored_name,original_name,file_type,file_size,uploaded_by_role,uploaded_by_name)
               VALUES (?,?,?,?,?,?,?)""",
            (chapter_id, stored, safe_original, ftype, size, u["role"], u["display_name"]))
    return jsonify({"ok": True, "stored_name": stored, "size": size}), 201


@app.route("/api/files/<int:file_id>/delete", methods=["POST"])
@require_role("trainer", "superadmin")
def chapter_file_delete(file_id):
    rec = fetch_one("SELECT * FROM chapter_files WHERE id = ?", (file_id,))
    if not rec:
        return jsonify({"error": "not found"}), 404
    if rec["stored_name"] != "sample_chapter_material.pdf":
        try:
            os.remove(os.path.join(UPLOAD_DIR, rec["stored_name"]))
        except OSError:
            pass
    execute("DELETE FROM chapter_files WHERE id = ?", (file_id,))
    return jsonify({"ok": True})


@app.route("/api/files/<int:file_id>/download", methods=["GET"])
def chapter_file_download(file_id):
    rec = fetch_one("SELECT * FROM chapter_files WHERE id = ?", (file_id,))
    if not rec:
        abort(404)
    return send_from_directory(UPLOAD_DIR, rec["stored_name"],
                               as_attachment=True, download_name=rec["original_name"])


# ---------------------------------------------------------------------------
# Internship Files: upload / download
# ---------------------------------------------------------------------------
@app.route("/api/internships/<int:item_id>/upload/<doc_type>", methods=["POST"])
@require_role("superadmin", "admin")
def upload_internship_file(item_id, doc_type):
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    f = request.files["file"]
    if not f or f.filename == "":
        return jsonify({"error": "No file selected"}), 400

    allowed_types = ["offer_letter", "internship_report", "certificate", "lor"]
    if doc_type not in allowed_types:
        return jsonify({"error": "Invalid document type"}), 400

    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in ALLOWED_EXT:
        return jsonify({"error": f"File type .{ext} not allowed"}), 400

    col_map = {
        "offer_letter": "offer_letter_file",
        "internship_report": "internship_report_file",
        "certificate": "certificate_file",
        "lor": "lor_file"
    }
    col = col_map[doc_type]
    
    stored = f"internship_{item_id}_{doc_type}_{uuid.uuid4().hex[:8]}.{ext}"
    path = os.path.join(UPLOAD_DIR, stored)
    f.save(path)

    # Clean up old file if exists
    old_row = fetch_one(f"SELECT {col} FROM internships WHERE id = ?", (item_id,))
    if old_row and old_row[col]:
        try:
            os.remove(os.path.join(UPLOAD_DIR, old_row[col]))
        except OSError:
            pass

    execute(f"UPDATE internships SET {col} = ? WHERE id = ?", (stored, item_id))
    return jsonify({"ok": True, "filename": stored}), 200

@app.route("/api/internships/files/<filename>", methods=["GET"])
def download_internship_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)
@app.route("/api/internships/<int:item_id>/delete/<doc_type>", methods=["POST"])
@require_role("superadmin", "admin")
def delete_internship_file(item_id, doc_type):
    allowed_types = ["offer_letter", "internship_report", "certificate", "lor"]
    if doc_type not in allowed_types:
        return jsonify({"error": "Invalid document type"}), 400

    col_map = {
        "offer_letter": "offer_letter_file",
        "internship_report": "internship_report_file",
        "certificate": "certificate_file",
        "lor": "lor_file"
    }
    col = col_map[doc_type]
    
    old_row = fetch_one(f"SELECT {col} FROM internships WHERE id = ?", (item_id,))
    if old_row and old_row[col]:
        try:
            os.remove(os.path.join(UPLOAD_DIR, old_row[col]))
        except OSError:
            pass
        execute(f"UPDATE internships SET {col} = NULL WHERE id = ?", (item_id,))
        
    return jsonify({"ok": True}), 200


# ---------------------------------------------------------------------------
# Bulk upload (CSV / Excel) — routes rows to the right section by filename
# ---------------------------------------------------------------------------
# Friendly header aliases -> actual column names, applied per entity.
BULK_HEADER_ALIASES = {
    "s.no": None, "sno": None, "sr no": None, "serial": None, "id": None,
    "full name": "name", "student name": "name", "trainer name": "name",
    "name": "name", "email id": "email", "e-mail": "email", "mail": "email",
    "mobile": "phone", "mobile no": "phone", "phone no": "phone",
    "contact": "phone", "university": "institution", "college": "institution",
    "company": "company_name", "company name": "company_name",
    "stipend amount": "stipend", "visitor card id no": "visitor_card_id",
    "visitor card": "visitor_card_id", "payment": "payment_type",
}

# For FK columns we let users supply a *name* instead of an id. Maps the
# field -> (lookup table, the header keywords that should resolve to it).
BULK_FK_RESOLVERS = {
    "project_id":  ("projects",  ["project", "project name", "project_name"]),
    "course_id":   ("courses",   ["course", "course name", "course_name"]),
    "module_id":   ("modules",   ["module", "module name", "module_name"]),
    "chapter_id":  ("chapters",  ["chapter", "chapter name", "chapter_name"]),
    "trainer_id":  ("trainers",  ["trainer", "trainer name", "trainer_name"]),
    "student_id":  ("students",  ["student", "student name", "student_name"]),
    "skill_id":    ("skills",    ["skill", "skill name", "skill_name"]),
    "activity_id": ("activities",["activity", "activity name", "activity_name"]),
}


def _norm_header(h):
    return str(h or "").strip().lower().replace("_", " ").replace("-", " ")


def _detect_entity(filename):
    """Pick the entity whose name matches the end of the filename (no ext).

    e.g. 'march_2026_students.csv' -> 'students'.
    Longer entity names win so 'student_attendance' beats 'students'.
    """
    base = os.path.splitext(os.path.basename(filename))[0].lower()
    base = base.replace("-", "_").replace(" ", "_")
    candidates = []
    for ent in ENTITY_REGISTRY:
        # match the entity name as a trailing token (or whole-word) in the file name
        if base == ent or base.endswith("_" + ent) or base.endswith(ent):
            candidates.append(ent)
    if not candidates:
        return None
    return max(candidates, key=len)


def _parse_rows(file_storage, filename):
    """Return (headers, list_of_row_dicts) from a CSV or Excel upload."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "csv":
        import csv, io
        raw = file_storage.read()
        text = raw.decode("utf-8-sig", errors="replace")
        reader = csv.reader(io.StringIO(text))
        rows = [r for r in reader if any((c or "").strip() for c in r)]
        if not rows:
            return [], []
        headers = rows[0]
        data = []
        for r in rows[1:]:
            data.append({headers[i]: (r[i] if i < len(r) else "") for i in range(len(headers))})
        return headers, data
    elif ext in ("xlsx", "xlsm"):
        import openpyxl
        wb = openpyxl.load_workbook(file_storage, read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        rows = [r for r in rows if r and any(c is not None and str(c).strip() for c in r)]
        if not rows:
            return [], []
        headers = [str(h) if h is not None else "" for h in rows[0]]
        data = []
        for r in rows[1:]:
            data.append({headers[i]: (r[i] if i < len(r) and r[i] is not None else "")
                         for i in range(len(headers))})
        return headers, data
    else:
        raise ValueError("Only .csv, .xlsx and .xlsm files are supported")


def _resolve_row(entity, raw_row):
    """Map a raw spreadsheet row (friendly headers) to the entity's columns."""
    info = ENTITY_REGISTRY[entity]
    allowed = set(info["fields"])
    db = get_db()

    # Pre-normalise the row: {normalised_header: value}
    norm = {}
    for k, v in raw_row.items():
        norm[_norm_header(k)] = v

    body = {}
    # 1) direct + aliased column matches
    for nh, val in norm.items():
        if val is None or str(val).strip() == "":
            continue
        target = None
        underscored = nh.replace(" ", "_")
        if underscored in allowed:
            target = underscored
        elif nh in BULK_HEADER_ALIASES and BULK_HEADER_ALIASES[nh] in allowed:
            target = BULK_HEADER_ALIASES[nh]
        if target:
            body[target] = str(val).strip()

    # 2) FK resolution by name (only for FK fields this entity actually has)
    for fk_field, (lookup_table, keywords) in BULK_FK_RESOLVERS.items():
        if fk_field not in allowed:
            continue
        # already provided as an id?
        if fk_field in body and str(body[fk_field]).isdigit():
            continue
        # find a header that looks like this FK's name
        for kw in keywords:
            kwn = _norm_header(kw)
            if kwn in norm and str(norm[kwn]).strip():
                nameval = str(norm[kwn]).strip()
                if nameval.isdigit():
                    body[fk_field] = nameval
                else:
                    found = db.execute(
                        f"SELECT id FROM {lookup_table} WHERE lower(name) = ?",
                        (nameval.lower(),)).fetchone()
                    if found:
                        body[fk_field] = found[0]
                break
    return body


@app.route("/api/bulk-upload", methods=["POST"])
@require_role("superadmin", "admin")
def bulk_upload():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    f = request.files["file"]
    if not f or f.filename == "":
        return jsonify({"error": "No file selected"}), 400

    filename = f.filename
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("csv", "xlsx", "xlsm"):
        return jsonify({"error": "Please upload a .csv or .xlsx file"}), 400

    entity = _detect_entity(filename)
    if not entity:
        return jsonify({
            "error": "Could not detect the section from the file name. "
                     "Name the file so it ends with the section, e.g. "
                     "'my_data_students.csv' or 'list_trainers.xlsx'.",
            "known_sections": sorted(ENTITY_REGISTRY.keys()),
        }), 400

    try:
        headers, rows = _parse_rows(f, filename)
    except Exception as e:
        return jsonify({"error": f"Could not read file: {e}"}), 400

    if not rows:
        return jsonify({"error": "The file has no data rows"}), 400

    info = ENTITY_REGISTRY[entity]
    table = info["table"]
    after_create = info["after_create"]

    inserted, skipped, errors = 0, 0, []
    for idx, raw in enumerate(rows, start=2):  # row 1 is the header
        body = _resolve_row(entity, raw)
        if not body:
            skipped += 1
            errors.append(f"Row {idx}: no matching columns, skipped")
            continue
        cols = list(body.keys())
        vals = [body[c] for c in cols]
        placeholders = ",".join(["?"] * len(cols))
        try:
            cur = execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})", vals)
            inserted += 1
            if after_create:
                try:
                    after_create(cur.lastrowid, body)
                except Exception as e:
                    print(f"[bulk after_create:{entity}] {e}")
        except Exception as e:
            skipped += 1
            errors.append(f"Row {idx}: {e}")

    return jsonify({
        "ok": True,
        "entity": entity,
        "inserted": inserted,
        "skipped": skipped,
        "total": len(rows),
        "errors": errors[:15],   # cap the list returned
    })


@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "not found", "message": str(e.description)}), 404
    return redirect("/login")


@app.errorhandler(500)
def server_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "server error", "message": str(e)}), 500
    return "Internal Server Error", 500


if __name__ == "__main__":
    # debug=True is fine for local development; turn off for production.
    app.run(host="127.0.0.1", port=5000, debug=True)

#app.py file is the main backend file that integrates the database to the frontend.The bulk upload option is also included.