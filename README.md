# Cyient Foundation CSR Dashboard

A Flask + SQLite CSR prototype with three role-based portals:
**Super Admin**, **Trainer**, and **Student** — each with real login
(passwords hashed and stored in SQLite), file uploads, tickets,
certificates, attendance, feedback and chapter management.

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 → you'll land on the role-selection page.

> **Important:** The database schema changed in this version. If you have an
> old `instance/crm.db`, delete it (or run `RESEED=1 python app.py`) so the new
> tables (users, tickets, certificates, chapter_files, student_chapter_status)
> are created and seeded.

## Login credentials

Default password for **every** seeded account: `cyient@123`

| Role        | Example username                       |
|-------------|----------------------------------------|
| Super Admin | `pavan.kumar@cyientfoundation.org`     |
| Trainer     | `anil.reddy@cyient.org`                |
| Student     | `student001@learner.cyient.org`        |

Usernames are the **emails** stored in the system. When a Super Admin adds a
new administrator / trainer / student, a login is **auto-created** for that
email with the default password (and a "must change password" flag).

Forgot-password is on each login page (prototype style: enter your email and a
new password — no email server needed).

## Portals

- **Student** — Dashboard, Chapter Management (view/download PDFs, set progress),
  Attendance, Certificates, Tickets, Feedback, Change Password.
- **Trainer** — Dashboard, Chapter Management (upload PDFs, set status),
  Student Management (add/edit), Mark Attendance, View Attendance, Certificates
  (view all issued), Tickets, Feedback, Change Password.
- **Super Admin** — full CRM admin board + Ticket Management, Certificate
  Management, Feedback Management, Change Password.

## File storage

Uploaded files (PDFs/videos) are saved on disk under `instance/uploads/`, and
only their metadata (name, size, type, chapter) is stored in SQLite. This keeps
the database small and handles videos well — the standard approach for real apps.
Max upload size is 50 MB; allowed types: pdf, mp4, webm, mov, png, jpg, jpeg,
ppt, pptx, doc, docx.


## What's new in this version

### Non-destructive database migration
On every startup the app now patches any **missing columns** into an existing
`crm.db` (e.g. the internship detail columns `payment_type`, `visitor_card_id`,
`reporting_manager`, and the document-file columns) **without deleting your
data**. So if internships were failing to save because of a missing column, just
run the app again — it self-heals. (A full reset with `RESEED=1 python app.py`
is still available if you want fresh sample data.)

### Bulk upload (CSV / Excel)
Super Admins get a **Bulk Upload** button in the top bar. Upload a `.csv` or
`.xlsx` file and the section is detected from the **end of the file name**:

| File name ends with… | Goes to |
|----------------------|---------|
| `..._students.csv`   | Students |
| `..._trainers.xlsx`  | Trainers |
| `..._projects.csv`   | Projects |
| `..._volunteers.csv` | Volunteers |
| `..._internships.csv`| Internships |
| …any section name    | that section |

- Column headers can be the exact field names or friendly names
  (`Full Name`, `Email ID`, `Mobile No`, `Company`, `University`…).
- Foreign keys can be given **by name** — e.g. a `Course` or `Project` column
  with the name in it is automatically resolved to the right id.
- Students/Trainers imported in bulk get their **login auto-created**
  (default password `cyient@123`).
- After import you're taken straight to that section to see the new rows.

Requires `openpyxl` (added to `requirements.txt`) for Excel files; CSV needs
nothing extra.


## Fixes in this build (presentation-ready to show in the company meeting)
- **Role-selection page now perfectly centered** — the grid was set to 4 columns
  while there are only 3 roles (Super Admin / Trainer / Student), which pushed the
  cards left of centre. Fixed to 3 columns + vertical centering.
- **Charts work offline** — Chart.js is now bundled locally in
  `static/vendor/chart.umd.js` instead of loaded from a CDN, so the Master Board
  charts render even with no internet during a presentation.
