/* ===================================================================
   portal.js — shared SPA framework for the Student & Trainer portals.
   Driven by window.PORTAL = { role: 'student'|'trainer' }.
   Reuses UI (ui.js) for toasts, modals, badges, formatters.
   =================================================================== */
(() => {
  'use strict';

  const ROLE = (window.PORTAL && window.PORTAL.role) || 'student';

  // ---- tiny fetch helper -------------------------------------------------
  async function req(path, opts = {}) {
    const init = { method: opts.method || 'GET', headers: {} };
    if (opts.body !== undefined) {
      init.headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(opts.body);
    }
    const res = await fetch(path, init);
    const text = await res.text();
    let data = null;
    if (text) { try { data = JSON.parse(text); } catch { data = { raw: text }; } }
    if (!res.ok) throw new Error((data && (data.error || data.message)) || `HTTP ${res.status}`);
    return data;
  }

  // ---- element handles ---------------------------------------------------
  const elNav     = document.getElementById('sidebar-nav');
  const elContent = document.getElementById('content');
  const elTitle   = document.getElementById('page-title');
  const elBc      = document.getElementById('bc-section');
  const elShell   = document.querySelector('.app-shell');

  // ---- icons -------------------------------------------------------------
  const I = {
    grid:    '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>',
    book:    '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
    check:   '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    ticket:  '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2z"/></svg>',
    key:     '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3"/></svg>',
    edit:    '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>',
    award:   '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/></svg>',
    users:   '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    clock:   '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    clip:    '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 2h6a2 2 0 0 1 2 2v2H7V4a2 2 0 0 1 2-2z"/><rect x="4" y="6" width="16" height="16" rx="2"/></svg>',
    download:'<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>',
    upload:  '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>',
    trash:   '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>',
  };

  // ---- nav configs -------------------------------------------------------
  const NAV = {
    student: [
      { key: 'dashboard',    label: 'Dashboard',       icon: I.grid },
      { key: 'chapters',     label: 'Chapter Management', icon: I.book },
      { key: 'attendance',   label: 'My Attendance',   icon: I.check },
      { key: 'certificates', label: 'Certificates',    icon: I.award },
      { key: 'tickets',      label: 'Tickets',         icon: I.ticket },
      { key: 'feedback',     label: 'Feedback',        icon: I.edit },
      { key: 'password',     label: 'Change Password', icon: I.key },
    ],
    trainer: [
      { key: 'dashboard',     label: 'Dashboard',           icon: I.grid },
      { key: 'chapters',      label: 'Chapter Management',  icon: I.book },
      { key: 'students',      label: 'Student Management',  icon: I.users },
      { key: 'mark_att',      label: 'Mark Attendance',     icon: I.clip },
      { key: 'attendance',    label: 'View Attendance',     icon: I.check },
      { key: 'certificates',  label: 'Certificates',        icon: I.award },
      { key: 'tickets',       label: 'Tickets',             icon: I.ticket },
      { key: 'feedback',      label: 'Feedback',            icon: I.edit },
      { key: 'password',      label: 'Change Password',     icon: I.key },
    ],
  };

  const TITLES = {
    dashboard: 'Dashboard', chapters: 'Chapter Management', attendance: ROLE === 'student' ? 'My Attendance' : 'View Attendance',
    certificates: 'Certificates', tickets: 'Tickets', feedback: 'Feedback', password: 'Change Password',
    students: 'Student Management', mark_att: 'Mark Student Attendance',
  };

  // ---- sidebar -----------------------------------------------------------
  function buildSidebar() {
    elNav.innerHTML = (NAV[ROLE] || []).map((it) =>
      `<button class="nav-item" data-key="${it.key}" type="button">
         <span class="nav-icon">${it.icon}</span><span class="nav-label">${it.label}</span>
       </button>`).join('');
    elNav.querySelectorAll('.nav-item').forEach((b) =>
      b.addEventListener('click', () => { location.hash = '#' + b.dataset.key; elShell.classList.remove('mobile-open'); }));
  }
  function markActive(key) {
    elNav.querySelectorAll('.nav-item').forEach((b) => b.classList.toggle('active', b.dataset.key === key));
  }

  // ---- helpers -----------------------------------------------------------
  const esc = (s) => UI.escapeHtml(s == null ? '' : String(s));
  const dash = '<span class="muted">—</span>';

  function statCard(label, value, meta, icon, color) {
    return `<div class="stat-card">
      <div class="stat-icon ${color || ''}">${icon}</div>
      <div><div class="stat-label">${esc(label)}</div>
      <div class="stat-value">${value}</div>
      <div class="stat-meta">${esc(meta)}</div></div></div>`;
  }

  function tableHTML(cols, rows, rowFn) {
    if (!rows.length) return UI.emptyState('Nothing here yet', 'Records will appear here once available.');
    return `<div class="card table-card"><div class="table-wrap"><table class="data-table">
      <thead><tr>${cols.map((c) => `<th>${esc(c)}</th>`).join('')}</tr></thead>
      <tbody>${rows.map(rowFn).join('')}</tbody></table></div></div>`;
  }

  // =======================================================================
  //  STUDENT PAGES
  // =======================================================================
  const StudentPages = {
    async dashboard() {
      const d = await req('/api/student/summary');
      const s = d.student || {};
      const chapPct = d.chapters.total ? Math.round((d.chapters.completed / d.chapters.total) * 100) : 0;
      elContent.innerHTML = `
        <div class="welcome-banner">
          <h2>Welcome back, ${esc(s.name || 'Student')} </h2>
          <p>${esc(s.course_name || 'Your course')} • ${esc(s.batch || '')} • ${esc(s.institution || '')}</p>
        </div>
        <div class="stats-grid">
          ${statCard('Attendance', d.attendance.pct + '%', `${d.attendance.present}/${d.attendance.total} classes`, I.check, 'green')}
          ${statCard('Chapters Done', d.chapters.completed, `of ${d.chapters.total} • ${d.chapters.in_progress} in progress`, I.book, 'blue')}
          ${statCard('Certificates', d.certificates, 'earned', I.award, 'purple')}
          ${statCard('My Tickets', d.tickets, 'raised', I.ticket, 'orange')}
        </div>
        <div class="card">
          <div class="card-header"><div><h3 class="card-title">Course Progress</h3>
            <div class="card-subtitle">${d.chapters.completed} of ${d.chapters.total} chapters completed</div></div></div>
          <div class="progress-bar-lg"><div class="progress-fill" style="width:${chapPct}%"></div></div>
          <div class="progress-pct">${chapPct}% complete</div>
        </div>
        <div class="card">
          <div class="card-header"><div><h3 class="card-title">Recent Attendance</h3></div></div>
          ${tableHTML(['Date', 'Course', 'Session', 'Status'], d.recent_attendance, (r) =>
            `<tr><td>${UI.fmtDate(r.attendance_date)}</td><td>${esc(r.course_name) || dash}</td>
             <td>${esc(r.session)}</td><td>${UI.badge(r.status)}</td></tr>`)}
        </div>`;
    },

    async chapters() {
      const rows = await req('/api/student/chapters');
      elContent.innerHTML = `
        <div class="card table-card">
          <div class="table-toolbar"><div class="table-meta">
            <span class="badge badge-info">${rows.length} chapters</span></div></div>
          <div class="table-wrap"><table class="data-table">
            <thead><tr><th>Course</th><th>Module</th><th>Chapter</th><th>Type</th><th>Status</th><th>Material</th><th>Action</th></tr></thead>
            <tbody>${rows.map((r) => `
              <tr>
                <td>${esc(r.course_name) || dash}</td>
                <td>${esc(r.module_name) || dash}</td>
                <td><strong>${esc(r.chapter_name)}</strong></td>
                <td>${esc(r.content_type)}</td>
                <td>${UI.badge(r.status)}</td>
                <td><button class="btn btn-ghost btn-sm" data-files="${r.chapter_id}">${I.download} ${r.file_count} file(s)</button></td>
                <td>
                  <select class="mini-select" data-status="${r.chapter_id}">
                    ${['Not Started', 'In Progress', 'Completed'].map((s) =>
                      `<option${s === r.status ? ' selected' : ''}>${s}</option>`).join('')}
                  </select>
                </td>
              </tr>`).join('')}</tbody></table></div></div>`;
      elContent.querySelectorAll('[data-status]').forEach((sel) =>
        sel.addEventListener('change', async () => {
          try {
            await req('/api/student/chapter-status', { method: 'POST',
              body: { chapter_id: Number(sel.dataset.status), status: sel.value } });
            UI.toast('Progress updated', 'success');
          } catch (e) { UI.toast(e.message, 'danger'); }
        }));
      elContent.querySelectorAll('[data-files]').forEach((b) =>
        b.addEventListener('click', () => showFiles(Number(b.dataset.files), false)));
    },

    async attendance() {
      const rows = await req('/api/student/attendance');
      elContent.innerHTML = tableHTML(['Date', 'Course', 'Session', 'Status', 'Remarks'], rows, (r) =>
        `<tr><td>${UI.fmtDate(r.attendance_date)}</td><td>${esc(r.course_name) || dash}</td>
         <td>${esc(r.session)}</td><td>${UI.badge(r.status)}</td><td>${esc(r.remarks) || dash}</td></tr>`);
    },

    async certificates() {
      const rows = await req('/api/student/certificates');
      if (!rows.length) { elContent.innerHTML = UI.emptyState('No certificates yet', 'Certificates appear here once you complete a course.'); return; }
      elContent.innerHTML = `<div class="cert-grid">${rows.map((c) => certCard(c)).join('')}</div>`;
      elContent.querySelectorAll('[data-cert]').forEach((b) =>
        b.addEventListener('click', () => viewCertificate(rows.find((x) => String(x.id) === b.dataset.cert))));
      elContent.querySelectorAll('[data-cert-download]').forEach((b) =>
        b.addEventListener('click', () => downloadCertificate(rows.find((x) => String(x.id) === b.dataset.certDownload))));
    },

    tickets() { return ticketsPage(); },
    feedback() { return feedbackPage(); },
    password() { return passwordPage(); },
  };

  // =======================================================================
  //  TRAINER PAGES
  // =======================================================================
  const TrainerPages = {
    async dashboard() {
      const d = await req('/api/trainer/summary');
      const t = d.trainer || {};
      const chapPct = d.chapters.total ? Math.round((d.chapters.completed / d.chapters.total) * 100) : 0;
      elContent.innerHTML = `
        <div class="welcome-banner">
          <h2>Welcome, ${esc(t.name || 'Trainer')} </h2>
          <p>${esc(t.specialization || '')} • ${esc(t.qualification || '')}</p>
        </div>
        <div class="stats-grid">
          ${statCard('My Attendance', d.attendance.pct + '%', `${d.attendance.present}/${d.attendance.total} days`, I.check, 'green')}
          ${statCard('Hours Taught', UI.fmtNum(d.attendance.hours), 'total', I.clock, 'blue')}
          ${statCard('Chapters', `${d.chapters.completed}/${d.chapters.total}`, 'completed', I.book, 'orange')}
          ${statCard('Students', d.students.active, `of ${d.students.total} active`, I.users, 'purple')}
          ${statCard('Certificates', d.certificates, 'issued (all)', I.award, 'pink')}
        </div>
        <div class="card">
          <div class="card-header"><div><h3 class="card-title">Chapter Completion</h3>
            <div class="card-subtitle">${d.chapters.completed} of ${d.chapters.total} assigned chapters completed</div></div></div>
          <div class="progress-bar-lg"><div class="progress-fill" style="width:${chapPct}%"></div></div>
          <div class="progress-pct">${chapPct}% complete</div>
        </div>
        <div class="card">
          <div class="card-header"><div><h3 class="card-title">My Recent Attendance</h3></div></div>
          ${tableHTML(['Date', 'Status', 'Hours Taught'], d.recent_attendance, (r) =>
            `<tr><td>${UI.fmtDate(r.attendance_date)}</td><td>${UI.badge(r.status)}</td><td>${r.hours_taught}</td></tr>`)}
        </div>`;
    },

    async chapters() {
      const rows = await req('/api/trainer/chapters');
      elContent.innerHTML = `
        <div class="card table-card">
          <div class="table-toolbar"><div class="table-meta">
            <span class="badge badge-info">${rows.length} assigned chapters</span></div></div>
          <div class="table-wrap"><table class="data-table">
            <thead><tr><th>Course</th><th>Module</th><th>Chapter</th><th>Batch</th><th>Status</th><th>Material</th><th>Upload</th></tr></thead>
            <tbody>${rows.map((r) => `
              <tr>
                <td>${esc(r.course_name) || dash}</td>
                <td>${esc(r.module_name) || dash}</td>
                <td><strong>${esc(r.chapter_name)}</strong></td>
                <td>${esc(r.batch)}</td>
                <td><select class="mini-select" data-assign="${r.assignment_id}">
                  ${['Scheduled', 'In Progress', 'Completed', 'Cancelled'].map((s) =>
                    `<option${s === r.assignment_status ? ' selected' : ''}>${s}</option>`).join('')}
                </select></td>
                <td><button class="btn btn-ghost btn-sm" data-files="${r.chapter_id}">${I.download} ${r.file_count}</button></td>
                <td><button class="btn btn-primary btn-sm" data-upload="${r.chapter_id}">${I.upload} PDF</button></td>
              </tr>`).join('')}</tbody></table></div></div>`;
      elContent.querySelectorAll('[data-assign]').forEach((sel) =>
        sel.addEventListener('change', async () => {
          try {
            await req('/api/trainer/assignment-status', { method: 'POST',
              body: { assignment_id: Number(sel.dataset.assign), status: sel.value } });
            UI.toast('Chapter status updated', 'success');
          } catch (e) { UI.toast(e.message, 'danger'); }
        }));
      elContent.querySelectorAll('[data-files]').forEach((b) =>
        b.addEventListener('click', () => showFiles(Number(b.dataset.files), true)));
      elContent.querySelectorAll('[data-upload]').forEach((b) =>
        b.addEventListener('click', () => uploadFile(Number(b.dataset.upload))));
    },

    async students() {
      const rows = await req('/api/students');
      elContent.innerHTML = `
        <div class="card table-card">
          <div class="table-toolbar">
            <div class="table-meta"><span class="badge badge-info">${rows.length} students</span></div>
            <div class="table-actions"><button class="btn btn-primary btn-sm" id="add-student">+ Add Student</button></div>
          </div>
          <div class="table-wrap"><table class="data-table">
            <thead><tr><th>Name</th><th>Email</th><th>Course</th><th>Batch</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>${rows.map((r) => `
              <tr>
                <td><strong>${esc(r.name)}</strong></td>
                <td>${esc(r.email)}</td>
                <td>${esc(r.course_name) || dash}</td>
                <td>${esc(r.batch)}</td>
                <td>${UI.badge(r.status)}</td>
                <td><button class="btn btn-icon" data-edit="${r.id}" title="Edit">${I.edit}</button></td>
              </tr>`).join('')}</tbody></table></div></div>`;
      document.getElementById('add-student').addEventListener('click', () => editStudent(null));
      elContent.querySelectorAll('[data-edit]').forEach((b) =>
        b.addEventListener('click', () => editStudent(Number(b.dataset.edit))));
    },

    async mark_att() {
      elContent.innerHTML = `
        <div class="card" style="max-width:640px;">
          <div class="card-header"><div><h3 class="card-title">Mark Student Attendance</h3>
            <div class="card-subtitle">Record attendance for a class session.</div></div></div>
          <div id="mark-form"></div>
        </div>`;
      const students = await req('/api/options/students');
      const courses = await req('/api/options/courses');
      const wrap = document.getElementById('mark-form');
      wrap.innerHTML = `
        <div class="field"><label>Student <span class="req">*</span></label>
          <select id="m-student">${students.map((s) => `<option value="${s.id}">${esc(s.name)}</option>`).join('')}</select></div>
        <div class="field"><label>Course</label>
          <select id="m-course"><option value="">— select —</option>${courses.map((c) => `<option value="${c.id}">${esc(c.name)}</option>`).join('')}</select></div>
        <div class="field"><label>Date <span class="req">*</span></label><input type="date" id="m-date" value="${new Date().toISOString().slice(0, 10)}" /></div>
        <div class="field"><label>Session</label><select id="m-session"><option>Morning</option><option>Afternoon</option><option>Full Day</option></select></div>
        <div class="field"><label>Status <span class="req">*</span></label><select id="m-status"><option>Present</option><option>Absent</option><option>Late</option><option>Excused</option></select></div>
        <div class="field"><label>Remarks</label><input type="text" id="m-remarks" placeholder="Optional" /></div>
        <div style="margin-top:10px;"><button class="btn btn-primary" id="m-save">Save Attendance</button></div>`;
      document.getElementById('m-save').addEventListener('click', async () => {
        try {
          await req('/api/student_attendance', { method: 'POST', body: {
            student_id: Number(document.getElementById('m-student').value),
            course_id: document.getElementById('m-course').value ? Number(document.getElementById('m-course').value) : null,
            attendance_date: document.getElementById('m-date').value,
            session: document.getElementById('m-session').value,
            status: document.getElementById('m-status').value,
            remarks: document.getElementById('m-remarks').value,
          } });
          UI.toast('Attendance recorded', 'success');
          document.getElementById('m-remarks').value = '';
        } catch (e) { UI.toast(e.message, 'danger'); }
      });
    },

    async attendance() {
      const rows = await req('/api/student_attendance');
      elContent.innerHTML = `
        <div class="card table-card">
          <div class="table-toolbar"><div class="table-meta">
            <span class="badge badge-info">${rows.length} records</span></div></div>
          <div class="table-wrap"><table class="data-table">
            <thead><tr><th>Date</th><th>Student</th><th>Course</th><th>Session</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>${rows.slice(0, 200).map((r) => `
              <tr><td>${UI.fmtDate(r.attendance_date)}</td><td>${esc(r.student_name) || dash}</td>
              <td>${esc(r.course_name) || dash}</td><td>${esc(r.session)}</td><td>${UI.badge(r.status)}</td>
              <td><button class="btn btn-icon btn-ghost" data-edit-att="${r.id}" title="Edit">${I.edit}</button></td></tr>`).join('')}</tbody>
          </table></div></div>`;
          
      elContent.querySelectorAll('[data-edit-att]').forEach((btn) => {
        btn.addEventListener('click', async () => {
          const id = btn.dataset.editAtt;
          const att = rows.find(r => r.id == id);
          const v = await UI.openForm({ title: 'Edit Attendance', values: att, fields: [
            { key: 'session', label: 'Session', type: 'select', options: ['Morning', 'Afternoon', 'Full Day'] },
            { key: 'status', label: 'Status', type: 'select', options: ['Present', 'Absent', 'Late', 'Excused'] },
            { key: 'remarks', label: 'Remarks', full: true }
          ] });
          if (!v) return;
          try { await req(`/api/student_attendance/${id}`, { method: 'PUT', body: v }); UI.toast('Attendance updated', 'success'); TrainerPages.attendance(); }
          catch (e) { UI.toast(e.message, 'danger'); }
        });
      });
    },

    async certificates() {
      const rows = await req('/api/trainer/certificates');
      const issued = rows.filter((r) => r.status === 'Issued').length;
      elContent.innerHTML = `
        <div class="stats-grid">
          ${statCard('Total Certificates', rows.length, 'all students', I.award, 'purple')}
          ${statCard('Issued', issued, 'completed students', I.check, 'green')}
        </div>
        <div class="card table-card">
          <div class="table-toolbar"><div class="table-meta"><span class="badge badge-info">${rows.length} certificates</span></div></div>
          <div class="table-wrap"><table class="data-table">
            <thead><tr><th>Cert No.</th><th>Student</th><th>Course</th><th>Grade</th><th>Issued</th><th>Status</th><th></th></tr></thead>
            <tbody>${rows.map((r) => `
              <tr><td><strong>${esc(r.certificate_no)}</strong></td><td>${esc(r.student_name) || dash}</td>
              <td>${esc(r.course_name) || dash}</td><td>${esc(r.grade)}</td><td>${UI.fmtDate(r.issued_date)}</td>
              <td>${UI.badge(r.status)}</td>
              <td><div style="display: flex; gap: 6px; align-items: center;">
                <button class="btn btn-ghost btn-sm" data-cert="${r.id}">View</button>
                <button class="btn btn-icon btn-ghost" data-cert-download-trainer="${r.id}" title="Download Certificate" style="padding: 4px 8px; display: flex; align-items: center; justify-content: center;">${I.download}</button>
              </div></td></tr>`).join('')}</tbody>
          </table></div></div>`;
      elContent.querySelectorAll('[data-cert]').forEach((b) =>
        b.addEventListener('click', () => viewCertificate(rows.find((x) => String(x.id) === b.dataset.cert))));
      elContent.querySelectorAll('[data-cert-download-trainer]').forEach((b) =>
        b.addEventListener('click', () => downloadTrainerCertificate(rows.find((x) => String(x.id) === b.dataset.certDownloadTrainer))));
    },

    tickets() { return ticketsPage(); },
    feedback() { return feedbackPage(); },
    password() { return passwordPage(); },
  };

  // =======================================================================
  //  SHARED PAGES (tickets, feedback, password)
  // =======================================================================
  async function ticketsPage() {
    const rows = await req('/api/me/tickets');
    elContent.innerHTML = `
      <div class="card table-card">
        <div class="table-toolbar">
          <div class="table-meta"><span class="badge badge-info">${rows.length} tickets</span></div>
          <div class="table-actions"><button class="btn btn-primary btn-sm" id="raise-ticket">+ Raise Ticket</button></div>
        </div>
        <div class="table-wrap"><table class="data-table">
          <thead><tr><th>#</th><th>Subject</th><th>Category</th><th>Priority</th><th>Status</th><th>Response</th><th>Raised</th><th>Actions</th></tr></thead>
          <tbody>${rows.map((r) => `
            <tr><td>#${r.id}</td><td><strong>${esc(r.subject)}</strong></td><td>${esc(r.category)}</td>
            <td>${UI.badge(r.priority)}</td><td>${UI.badge(r.status)}</td>
            <td>${esc(r.response) || dash}</td><td>${UI.fmtDate(r.created_at)}</td>
            <td>
              <div class="row-actions">
                <button class="btn btn-icon btn-ghost" data-edit-ticket="${r.id}" title="Edit">${I.edit}</button>
                <button class="btn btn-icon btn-ghost btn-icon-danger" data-delete-ticket="${r.id}" title="Delete">${I.trash}</button>
              </div>
            </td></tr>`).join('')}</tbody>
        </table></div></div>`;
        
    document.getElementById('raise-ticket').addEventListener('click', async () => {
      const v = await UI.openForm({ title: 'Raise a Ticket', fields: [
        { key: 'subject', label: 'Subject', required: true, full: true },
        { key: 'category', label: 'Category', type: 'select', options: ['General', 'Technical', 'Content', 'Attendance', 'Other'] },
        { key: 'priority', label: 'Priority', type: 'select', required: true, options: ['Low', 'Medium', 'High', 'Urgent'] },
        { key: 'description', label: 'Description', type: 'textarea', full: true },
      ] });
      if (!v) return;
      try { await req('/api/me/tickets', { method: 'POST', body: v }); UI.toast('Ticket raised', 'success'); ticketsPage(); }
      catch (e) { UI.toast(e.message, 'danger'); }
    });

    elContent.querySelectorAll('[data-edit-ticket]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const id = btn.dataset.editTicket;
        const ticket = rows.find(r => r.id == id);
        const v = await UI.openForm({ title: 'Edit Ticket', values: ticket, fields: [
          { key: 'subject', label: 'Subject', required: true, full: true },
          { key: 'category', label: 'Category', type: 'select', options: ['General', 'Technical', 'Content', 'Attendance', 'Other'] },
          { key: 'priority', label: 'Priority', type: 'select', required: true, options: ['Low', 'Medium', 'High', 'Urgent'] },
          { key: 'description', label: 'Description', type: 'textarea', full: true },
        ] });
        if (!v) return;
        try { await req(`/api/me/tickets/${id}`, { method: 'PUT', body: v }); UI.toast('Ticket updated', 'success'); ticketsPage(); }
        catch (e) { UI.toast(e.message, 'danger'); }
      });
    });

    elContent.querySelectorAll('[data-delete-ticket]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const id = btn.dataset.deleteTicket;
        if (!(await UI.confirmAction('Delete this ticket?', 'Delete'))) return;
        try { await req(`/api/me/tickets/${id}`, { method: 'DELETE' }); UI.toast('Ticket deleted', 'success'); ticketsPage(); }
        catch (e) { UI.toast(e.message, 'danger'); }
      });
    });
  }

  async function feedbackPage() {
    const rows = await req('/api/me/feedback');
    elContent.innerHTML = `
      <div class="card table-card">
        <div class="table-toolbar">
          <div class="table-meta"><span class="badge badge-info">${rows.length} submitted</span></div>
          <div class="table-actions"><button class="btn btn-primary btn-sm" id="give-feedback">+ Give Feedback</button></div>
        </div>
        <div class="table-wrap"><table class="data-table">
          <thead><tr><th>Subject</th><th>Comments</th><th>Rating</th><th>Status</th><th>Date</th><th>Actions</th></tr></thead>
          <tbody>${rows.map((r) => `
            <tr><td><strong>${esc(r.subject)}</strong></td><td>${esc(r.comments)}</td>
            <td>${'★'.repeat(r.rating || 0)}</td><td>${UI.badge(r.status)}</td><td>${UI.fmtDate(r.created_at)}</td>
            <td>
              <div class="row-actions">
                <button class="btn btn-icon btn-ghost" data-edit-feedback="${r.id}" title="Edit">${I.edit}</button>
                <button class="btn btn-icon btn-ghost btn-icon-danger" data-delete-feedback="${r.id}" title="Delete">${I.trash}</button>
              </div>
            </td></tr>`).join('')}</tbody>
        </table></div></div>`;
        
    document.getElementById('give-feedback').addEventListener('click', async () => {
      const v = await UI.openForm({ title: 'Submit Feedback', fields: [
        { key: 'subject', label: 'Subject', required: true, full: true },
        { key: 'comments', label: 'Your feedback', type: 'textarea', required: true, full: true },
        { key: 'rating', label: 'Rating (1-5)', type: 'number', min: 1, max: 5 },
      ] });
      if (!v) return;
      v.rating = Number(v.rating || 5);
      try { await req('/api/me/feedback', { method: 'POST', body: v }); UI.toast('Feedback submitted', 'success'); feedbackPage(); }
      catch (e) { UI.toast(e.message, 'danger'); }
    });

    elContent.querySelectorAll('[data-edit-feedback]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const id = btn.dataset.editFeedback;
        const feedback = rows.find(r => r.id == id);
        const v = await UI.openForm({ title: 'Edit Feedback', values: feedback, fields: [
          { key: 'subject', label: 'Subject', required: true, full: true },
          { key: 'comments', label: 'Your feedback', type: 'textarea', required: true, full: true },
          { key: 'rating', label: 'Rating (1-5)', type: 'number', min: 1, max: 5 },
        ] });
        if (!v) return;
        v.rating = Number(v.rating || 5);
        try { await req(`/api/me/feedback/${id}`, { method: 'PUT', body: v }); UI.toast('Feedback updated', 'success'); feedbackPage(); }
        catch (e) { UI.toast(e.message, 'danger'); }
      });
    });

    elContent.querySelectorAll('[data-delete-feedback]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const id = btn.dataset.deleteFeedback;
        if (!(await UI.confirmAction('Delete this feedback?', 'Delete'))) return;
        try { await req(`/api/me/feedback/${id}`, { method: 'DELETE' }); UI.toast('Feedback deleted', 'success'); feedbackPage(); }
        catch (e) { UI.toast(e.message, 'danger'); }
      });
    });
  }

  function passwordPage() {
    elContent.innerHTML = `
      <div class="card" style="max-width:460px;">
        <div class="card-header"><div><h3 class="card-title">Change Password</h3>
          <div class="card-subtitle">Update your account password.</div></div></div>
        <div class="field"><label>Current Password <span class="req">*</span></label><input type="password" id="cp-current" /></div>
        <div class="field"><label>New Password <span class="req">*</span></label><input type="password" id="cp-new" /></div>
        <div class="field"><label>Confirm New Password <span class="req">*</span></label><input type="password" id="cp-confirm" /></div>
        <div style="margin-top:10px;"><button class="btn btn-primary" id="cp-save">Update Password</button></div>
      </div>`;
    document.getElementById('cp-save').addEventListener('click', async () => {
      const cur = document.getElementById('cp-current').value;
      const nw = document.getElementById('cp-new').value;
      const cf = document.getElementById('cp-confirm').value;
      if (!cur || !nw) return UI.toast('Fill all fields', 'danger');
      if (nw !== cf) return UI.toast('New passwords do not match', 'danger');
      try {
        await req('/api/auth/change-password', { method: 'POST', body: { current_password: cur, new_password: nw } });
        UI.toast('Password updated successfully', 'success');
        ['cp-current', 'cp-new', 'cp-confirm'].forEach((id) => document.getElementById(id).value = '');
      } catch (e) { UI.toast(e.message, 'danger'); }
    });
  }

  // =======================================================================
  //  SHARED WIDGETS (files, upload, certificate, student edit)
  // =======================================================================
  async function showFiles(chapterId, canManage) {
    let files;
    try { files = await req(`/api/chapters/${chapterId}/files`); }
    catch (e) { return UI.toast(e.message, 'danger'); }
    const body = files.length
      ? `<ul class="file-list">${files.map((f) => `
          <li><span>${f.file_type === 'pdf' ? '📄' : f.file_type === 'video' ? '🎬' : '📎'} ${esc(f.original_name)}
            <span class="muted">(${(f.file_size / 1024).toFixed(0)} KB)</span></span>
            <span class="file-actions">
              <a class="btn btn-ghost btn-sm" href="/api/files/${f.id}/download">Download</a>
              ${canManage ? `<button class="btn btn-icon btn-icon-danger" data-del="${f.id}" title="Delete">${I.trash}</button>` : ''}
            </span></li>`).join('')}</ul>`
      : `<p class="muted">No files uploaded for this chapter yet.</p>`;
    openInfoModal('Chapter Materials', body, (modal) => {
      modal.querySelectorAll('[data-del]').forEach((b) =>
        b.addEventListener('click', async () => {
          if (!(await UI.confirmAction('Delete this file?', 'Delete'))) return;
          try { await req(`/api/files/${b.dataset.del}/delete`, { method: 'POST' }); UI.toast('File deleted', 'success'); closeInfoModal(); showFiles(chapterId, canManage); }
          catch (e) { UI.toast(e.message, 'danger'); }
        }));
    });
  }

  function uploadFile(chapterId) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.mp4,.webm,.mov,.png,.jpg,.jpeg,.ppt,.pptx,.doc,.docx';
    input.addEventListener('change', async () => {
      if (!input.files.length) return;
      const fd = new FormData();
      fd.append('file', input.files[0]);
      UI.toast('Uploading…', 'info');
      try {
        const res = await fetch(`/api/chapters/${chapterId}/files`, { method: 'POST', body: fd });
        if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.error || 'Upload failed'); }
        UI.toast('File uploaded', 'success');
        if (location.hash === '#chapters') route();
      } catch (e) { UI.toast(e.message, 'danger'); }
    });
    input.click();
  }

  function certCard(c) {
    return `<div class="cert-card">
      <div class="cert-ribbon">${esc(c.status)}</div>
      <div class="cert-icon">${I.award}</div>
      <div class="cert-course">${esc(c.course_name) || 'Course'}</div>
      <div class="cert-no">${esc(c.certificate_no)}</div>
      <div class="cert-meta">Grade ${esc(c.grade)} • ${UI.fmtDate(c.issued_date)}</div>
      <div class="cert-actions" style="display: flex; gap: 8px; margin-top: 10px;">
        <button class="btn btn-primary btn-sm" data-cert="${c.id}" style="flex: 1;">View Certificate</button>
        <button class="btn btn-ghost btn-sm" data-cert-download="${c.id}" title="Download Certificate" style="flex: 0 0 auto; padding: 6px 12px;">${I.download}</button>
      </div>
    </div>`;
  }

  function viewCertificate(c) {
    if (!c) return;
    const name = c.student_name || (window.PORTAL && window.PORTAL.name) || 'Student';
    const body = `
      <div class="certificate">
        <div class="certificate-inner">
          <div class="cert-head">CYIENT FOUNDATION</div>
          <div class="cert-sub">Certificate of Completion</div>
          <div class="cert-line">This is proudly presented to</div>
          <div class="cert-name">${esc(name)}</div>
          <div class="cert-line">for successfully completing the course</div>
          <div class="cert-course-name">${esc(c.course_name) || 'Course'}</div>
          <div class="cert-footer">
            <div><div class="cert-val">${esc(c.certificate_no)}</div><div class="cert-cap">Certificate No.</div></div>
            <div><div class="cert-val">${esc(c.grade)}</div><div class="cert-cap">Grade</div></div>
            <div><div class="cert-val">${UI.fmtDate(c.issued_date)}</div><div class="cert-cap">Issued</div></div>
          </div>
        </div>
      </div>`;
    openInfoModal('', body);
  }

  function downloadCertificate(c) {
    if (!c) return;
    const url = `/api/${ROLE}/certificates/${c.id}/download`;
    const link = document.createElement('a');
    link.href = url;
    link.download = `Certificate_${c.certificate_no || c.id}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  function downloadTrainerCertificate(c) {
    if (!c) return;
    const url = `/api/trainer/certificates/${c.id}/download`;
    const link = document.createElement('a');
    link.href = url;
    link.download = `Certificate_${c.certificate_no || c.id}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  async function editStudent(id) {
    let values = {};
    if (id) { try { values = await req(`/api/students/${id}`); } catch (e) { return UI.toast(e.message, 'danger'); } }
    const courses = await req('/api/options/courses');
    const projects = await req('/api/options/projects');
    const v = await UI.openForm({
      title: id ? 'Edit Student' : 'Add Student',
      values,
      fields: [
        { key: 'name', label: 'Full name', required: true, full: true },
        { key: 'email', label: 'Email', type: 'email', required: true },
        { key: 'phone', label: 'Phone' },
        { key: 'project_id', label: 'Project', type: 'select', options: projects.map((p) => ({ value: p.id, label: p.name })) },
        { key: 'course_id', label: 'Course', type: 'select', options: courses.map((c) => ({ value: c.id, label: c.name })) },
        { key: 'batch', label: 'Batch' },
        { key: 'status', label: 'Status', type: 'select', required: true, options: ['Active', 'Inactive', 'Completed', 'Dropped'] },
        { key: 'gender', label: 'Gender', type: 'select', options: ['Male', 'Female', 'Other'] },
        { key: 'institution', label: 'Institution', full: true },
      ],
    });
    if (!v) return;
    try {
      if (id) { await req(`/api/students/${id}`, { method: 'PUT', body: v }); UI.toast('Student updated', 'success'); }
      else { await req('/api/students', { method: 'POST', body: v }); UI.toast('Student added (login auto-created)', 'success'); }
      route();
    } catch (e) { UI.toast(e.message, 'danger'); }
  }

  // ---- generic info modal (uses confirm-backdrop shell) ------------------
  function openInfoModal(title, bodyHTML, after) {
    let m = document.getElementById('info-backdrop');
    if (!m) {
      m = document.createElement('div');
      m.className = 'modal-backdrop';
      m.id = 'info-backdrop';
      m.innerHTML = `<div class="modal info-modal"><header class="modal-header">
        <h3 id="info-title"></h3><button class="modal-close" id="info-close">×</button></header>
        <div class="modal-body" id="info-body"></div></div>`;
      document.body.appendChild(m);
    }
    m.querySelector('#info-title').textContent = title || '';
    m.querySelector('#info-body').innerHTML = bodyHTML;
    m.hidden = false;
    const close = () => closeInfoModal();
    m.querySelector('#info-close').onclick = close;
    m.onclick = (e) => { if (e.target === m) close(); };
    if (after) after(m);
  }
  function closeInfoModal() {
    const m = document.getElementById('info-backdrop');
    if (m) m.hidden = true;
  }

  // =======================================================================
  //  ROUTER
  // =======================================================================
  const PAGES = ROLE === 'trainer' ? TrainerPages : StudentPages;

  async function route() {
    const key = (location.hash || '#dashboard').replace(/^#/, '') || 'dashboard';
    const fn = PAGES[key] || PAGES.dashboard;
    markActive(PAGES[key] ? key : 'dashboard');
    elTitle.textContent = TITLES[key] || 'Dashboard';
    elBc.textContent = ROLE === 'trainer' ? 'Trainer Portal' : 'Student Portal';
    elContent.innerHTML = `<div class="loader"><div class="spinner"></div><div>Loading…</div></div>`;
    try { await fn(); }
    catch (e) {
      elContent.innerHTML = `<div class="card"><div class="empty-state"><h3>Could not load</h3><p>${esc(e.message)}</p></div></div>`;
      UI.toast(e.message, 'danger');
    }
  }

  // ---- topbar / notifications --------------------------------------------
  async function updateNotifBadge() {
    const badge = document.getElementById('notif-badge');
    if (!badge) return;
    try {
      const [tickets, feedbacks] = await Promise.all([
        req('/api/me/tickets'),
        req('/api/me/feedback')
      ]);
      const resolvedTickets = tickets.filter(t => t.status === 'Resolved' || t.status === 'Closed');
      const resolvedFeedbacks = feedbacks.filter(f => f.status === 'Resolved' || f.status === 'Addressed' || f.status === 'Reviewed');
      const allItems = [...resolvedTickets, ...resolvedFeedbacks];
      
      const lastRead = localStorage.getItem('lastReadNotifsTime_' + ROLE);
      let unreadCount = 0;
      
      if (!lastRead) {
        unreadCount = allItems.length;
      } else {
        const readTime = parseInt(lastRead, 10);
        unreadCount = allItems.filter(item => {
          const timeStr = item.updated_at || item.created_at;
          if (!timeStr) return true;
          const itemTime = new Date(timeStr.replace(' ', 'T') + 'Z').getTime();
          return itemTime > readTime;
        }).length;
      }
      
      if (unreadCount > 0) {
        badge.textContent = unreadCount;
        badge.hidden = false;
        badge.style.display = 'flex';
      } else {
        badge.hidden = true;
        badge.style.display = 'none';
      }
    } catch (err) {}
  }

  // ---- logout ------------------------------------------------------------
  function wireLogout() {
    const btn = document.getElementById('logout-action');
    if (btn) btn.addEventListener('click', async (e) => {
      e.preventDefault();
      try { await req('/api/auth/logout', { method: 'POST' }); } catch {}
      location.href = '/login';
    });
    const mob = document.getElementById('mobile-menu');
    if (mob) mob.addEventListener('click', () => elShell.classList.toggle('mobile-open'));

    const notifBtn = document.getElementById('notifications-action');
    if (notifBtn) {
      notifBtn.addEventListener('click', async () => {
        const badge = document.getElementById('notif-badge');
        if (badge) {
          badge.hidden = true;
          badge.style.display = 'none';
        }
        localStorage.setItem('lastReadNotifsTime_' + ROLE, Date.now());

        const overlay = document.createElement('div');
        overlay.className = 'modal-backdrop';
        overlay.innerHTML = `
          <div class="modal" style="max-width: 500px;">
            <header class="modal-header">
              <h3>Notifications</h3>
              <button class="modal-close" title="Close">×</button>
            </header>
            <div class="modal-body" style="padding: 20px; max-height: 60vh; overflow-y: auto;">
              <div id="notif-loading" style="text-align: center; color: var(--gray-500);">Loading...</div>
              <ul id="notif-list" style="list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px;"></ul>
            </div>
          </div>
        `;
        document.body.appendChild(overlay);

        const closeBtn = overlay.querySelector('.modal-close');
        const closeOverlay = (e) => {
          if (e.target === overlay || e.target === closeBtn) overlay.remove();
        };
        overlay.addEventListener('click', closeOverlay);

        try {
          const [tickets, feedbacks] = await Promise.all([
            req('/api/me/tickets'),
            req('/api/me/feedback')
          ]);

          const resolvedTickets = tickets.filter(t => t.status === 'Resolved' || t.status === 'Closed');
          const resolvedFeedbacks = feedbacks.filter(f => f.status === 'Resolved' || f.status === 'Addressed' || f.status === 'Reviewed');

          const items = [];
          resolvedTickets.forEach(t => {
            items.push({
              type: 'tickets',
              title: `Ticket ${t.status}: ${t.subject}`,
              desc: `Your ticket has been ${t.status}.`,
              timeStr: t.updated_at || t.created_at
            });
          });
          resolvedFeedbacks.forEach(f => {
            items.push({
              type: 'feedback',
              title: `Feedback ${f.status}: ${f.subject}`,
              desc: `Your feedback has been ${f.status}.`,
              timeStr: f.updated_at || f.created_at
            });
          });

          items.sort((a, b) => {
             const tA = new Date((a.timeStr || '').replace(' ', 'T') + 'Z').getTime() || 0;
             const tB = new Date((b.timeStr || '').replace(' ', 'T') + 'Z').getTime() || 0;
             return tB - tA;
          });

          overlay.querySelector('#notif-loading').remove();
          const list = overlay.querySelector('#notif-list');

          if (items.length === 0) {
            list.innerHTML = `<li style="text-align: center; color: var(--gray-500); padding: 20px;">No new notifications</li>`;
          } else {
            list.innerHTML = items.map(item => `
              <li style="padding: 12px; border-radius: 6px; background: #f8fafc; border: 1px solid #e2e8f0; display: flex; gap: 12px; align-items: flex-start; cursor: pointer; transition: background .15s;" onmouseover="this.style.background='#e2e8f0'" onmouseout="this.style.background='#f8fafc'" onclick="location.hash='#${item.type}'; document.body.removeChild(this.closest('.modal-backdrop'));">
                <div>
                  <div style="font-weight: 600; font-size: 14px; color: #1e293b;">${UI.escapeHtml(item.title)}</div>
                  <div style="font-size: 13px; color: #64748b; margin-top: 4px;">${UI.escapeHtml(item.desc)}</div>
                </div>
              </li>
            `).join('');
          }
        } catch (err) {
          const loader = overlay.querySelector('#notif-loading');
          if (loader) loader.textContent = 'Failed to load notifications.';
        }
      });
    }
  }

  function init() {
    buildSidebar();
    wireLogout();
    updateNotifBadge();
    window.addEventListener('hashchange', route);
    route();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();

// This is a placeholder for any global functions or variables that might be needed across different pages or components. You can add utility functions, constants, or any shared logic here that doesn't fit into the specific page modules above.