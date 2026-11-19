// Simple UI for the API. Every button calls the same routes you test in /docs.
// The server still checks every request with require_role(); hiding a card here
// is only for convenience, never for security.

let token = null;   // kept in memory only: refreshing the page logs you out
let me = null;      // the logged-in user from GET /auth/me

const $ = (id) => document.getElementById(id);

// Send a request with the login token. Returns the parsed JSON, or throws an Error
// carrying the server's "detail" message (e.g. 401 or 403).
async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (token) headers["Authorization"] = "Bearer " + token;
  if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.json);
  }
  const res = await fetch(path, { ...options, headers });
  if (!res.ok) {
    let detail = res.status + " " + res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail.map((d) => d.msg).join(", ");
    } catch (_) { /* not JSON */ }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  if (options.raw) return res;
  return res.status === 204 ? null : res.json();
}

function showMessage(text, isError = false) {
  const box = $("message");
  box.textContent = text;
  box.classList.toggle("error", isError);
  box.hidden = false;
}

// Build a table with textContent only (never innerHTML), so data from the
// database can't inject HTML or scripts into the page (XSS).
function fillTable(table, columns, rows, extra) {
  table.replaceChildren();
  if (rows.length === 0) {
    const caption = document.createElement("caption");
    caption.className = "empty";
    caption.textContent = "Nothing here yet.";
    table.append(caption);
    return;
  }
  const head = table.createTHead().insertRow();
  for (const [, label] of columns) {
    const th = document.createElement("th");
    th.textContent = label;
    head.append(th);
  }
  if (extra) head.append(document.createElement("th"));
  const body = table.createTBody();
  for (const row of rows) {
    const tr = body.insertRow();
    for (const [key] of columns) tr.insertCell().textContent = row[key] ?? "";
    if (extra) tr.insertCell().append(extra(row));
  }
}

// ---------- Login and logout ----------

$("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  $("login-error").textContent = "";
  const body = { username: form.username.value, password: form.password.value };
  if (form.totp_code.value) body.totp_code = form.totp_code.value;
  try {
    const data = await api("/auth/login", { method: "POST", json: body });
    token = data.access_token;
    form.reset();
    $("totp-row").hidden = true;
    await startDashboard();
  } catch (err) {
    if (err.message === "MFA code required") {
      $("totp-row").hidden = false;   // password was right: now ask for the code
      form.totp_code.focus();
    }
    $("login-error").textContent = err.message;
  }
});
// ---------- Forgot password (POST /auth/reset-password) ----------

function showReset(show) {
  $("login-form").hidden = show;
  $("forgot-link").hidden = show;
  $("reset-form").hidden = !show;
  $("reset-error").textContent = "";
}
$("forgot-link").addEventListener("click", () => showReset(true));
$("reset-cancel").addEventListener("click", () => showReset(false));

$("reset-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target;
  try {
    await api("/auth/reset-password", { method: "POST", json: {
      username: f.username.value, totp_code: f.totp_code.value, new_password: f.new_password.value } });
    f.reset();
    showReset(false);
    $("login-error").textContent = "Password changed. Log in with your new password.";
  } catch (err) { $("reset-error").textContent = err.message; }
});

$("logout").addEventListener("click", () => {
  token = null;
  me = null;
  $("app-view").hidden = true;
  $("who").hidden = true;
  $("message").hidden = true;
  $("login-view").hidden = false;
});

// ---------- Dashboard ----------

async function startDashboard() {
  me = await api("/auth/me");
  $("who-text").textContent = me.username + " (" + me.role + ")";
  $("who").hidden = false;
  $("login-view").hidden = true;
  $("app-view").hidden = false;
  $("message").hidden = true;

  // Show only the cards whose data-roles list contains this user's role.
  for (const el of document.querySelectorAll("#app-view [data-roles]")) {
    el.hidden = !el.dataset.roles.split(" ").includes(me.role);
  }
  showMfaStatus();
  const loaders = {
    student: [loadMyRecord, loadMaterials],
    instructor: [loadStudents, loadMaterials, loadAnonymized],
    admin: [loadStudents, loadAnonymized, loadUsers],
  }[me.role] || [];
  for (const load of loaders) {
    try { await load(); } catch (err) { showMessage(err.message, true); }
  }
}
// ---------- MFA setup (POST /auth/mfa/setup, then /auth/mfa/verify) ----------

function showMfaStatus() {
  $("mfa-status").textContent = me.mfa_enabled
    ? "MFA is on. You'll be asked for a code from your phone every time you log in."
    : "MFA is off. Turn it on so a stolen password alone can't open your account.";
  $("mfa-start").hidden = me.mfa_enabled;
  $("mfa-setup").hidden = true;
}

$("mfa-start").addEventListener("click", async () => {
  try {
    const data = await api("/auth/mfa/setup", { method: "POST" });
    // The QR code comes from our own server; it's shown as an image, never as HTML.
    $("mfa-secret").textContent = new URL(data.provisioning_uri).searchParams.get("secret");    $("mfa-setup").hidden = false;
    $("mfa-start").hidden = true;
  } catch (err) { showMessage(err.message, true); }
});

$("mfa-verify-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/auth/mfa/verify", { method: "POST", json: { code: e.target.code.value } });
    e.target.reset();
    me = await api("/auth/me");
    showMfaStatus();
    showMessage("MFA is on. Next time you log in, enter the code from your phone.");
  } catch (err) { showMessage(err.message, true); }
});

async function loadMyRecord() {
  const dl = $("my-record");
  dl.replaceChildren();
  try {
    const s = await api("/students/me");
    const fields = [["Student number", s.student_number], ["Name", s.full_name],
      ["Department", s.department], ["Birth year", s.birth_year], ["GPA", s.gpa]];
    for (const [label, value] of fields) {
      const dt = document.createElement("dt");
      const dd = document.createElement("dd");
      dt.textContent = label;
      dd.textContent = value;
      dl.append(dt, dd);
    }
  } catch (err) {
    dl.textContent = err.message;
  }
}

async function loadStudents() {
  const rows = await api("/students");
  const columns = [["student_number", "Number"], ["full_name", "Name"],
    ["department", "Department"], ["birth_year", "Born"]];
  if (me.role === "admin") columns.push(["gpa", "GPA"]);
  // Instructors get a GPA box and a Save button (PATCH /students/{id}/gpa).
  const gpaEditor = me.role === "instructor" ? (s) => {
    const wrap = document.createElement("span");
    const input = document.createElement("input");
    input.type = "number"; input.min = "0"; input.max = "4"; input.step = "0.01";
    input.value = s.gpa;
    input.className = "gpa";
    const save = document.createElement("button");
    save.textContent = "Save";
    save.addEventListener("click", async () => {
      try {
        await api("/students/" + s.id + "/gpa", { method: "PATCH", json: { gpa: Number(input.value) } });
        showMessage("GPA of " + s.full_name + " saved as " + input.value + ".");
      } catch (err) { showMessage(err.message, true); }
    });
    wrap.append(input, save);
    return wrap;
  } : null;
  fillTable($("students-table"), columns, rows, gpaEditor);
}

$("student-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target;
  const body = {
    student_number: f.student_number.value, full_name: f.full_name.value,
    birth_year: Number(f.birth_year.value), gender: f.gender.value,
    zip_code: f.zip_code.value, department: f.department.value,
    gpa: Number(f.gpa.value),
  };
  if (f.national_id.value) body.national_id = f.national_id.value;
  try {
    await api("/students", { method: "POST", json: body });
    showMessage("Student " + body.full_name + " added.");
    f.reset();
    await loadStudents();
  } catch (err) { showMessage(err.message, true); }
});

async function loadMaterials() {
  const rows = await api("/materials");
  const download = (m) => {
    const btn = document.createElement("button");
    btn.className = "secondary";
    btn.textContent = "Download";
    btn.addEventListener("click", async () => {
      // A plain link can't send the Authorization header, so fetch the file
      // with the token and hand it to the browser as a temporary blob URL.
      try {
        const res = await api("/materials/" + m.id + "/download", { raw: true });
        const url = URL.createObjectURL(await res.blob());
        const a = document.createElement("a");
        const match = /filename="?([^"]+)"?/.exec(res.headers.get("Content-Disposition") || "");
        a.href = url;
        a.download = match ? match[1] : m.title;
        a.click();
        URL.revokeObjectURL(url);
      } catch (err) { showMessage(err.message, true); }
    });
    return btn;
  };
  const shown = rows.map((m) => ({ ...m, uploaded_at: (m.uploaded_at || "").replace("T", " ").slice(0, 16) }));
  fillTable($("materials-table"), [["title", "Title"], ["uploaded_at", "Uploaded"]], shown, download);
}

$("upload-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target;
  const data = new FormData();          // multipart/form-data, like the /docs upload
  data.append("title", f.title.value);
  data.append("file", f.file.files[0]);
  try {
    await api("/materials", { method: "POST", body: data });
    showMessage("Uploaded " + f.title.value + ".");
    f.reset();
    await loadMaterials();
  } catch (err) { showMessage(err.message, true); }
});

async function loadAnonymized() {
  const rows = await api("/anonymized");
  fillTable($("anon-table"), [["age_range", "Age range"], ["gender", "Gender"],
    ["zip_prefix", "ZIP prefix"], ["department", "Department"], ["gpa", "GPA"]], rows);
}

async function loadUsers() {
  const rows = await api("/users");
    fillTable($("users-table"), [["id", "ID"], ["username", "Username"], ["role", "Role"],
    ["student_id", "Student ID"], ["mfa_enabled", "MFA on"]], rows.map((u) => ({ ...u, mfa_enabled: u.mfa_enabled ? "yes" : "no" })));
    
}

$("user-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target;
  try {
    await api("/users", { method: "POST",
      json: { username: f.username.value, password: f.password.value, role: f.role.value,
              student_number: f.student_number.value || null } });
    showMessage("User " + f.username.value + " created.");
    f.reset();
    await loadUsers();
  } catch (err) { showMessage(err.message, true); }
});
// Edit a user: send only the fields that were filled in (PATCH /users/{id}).
$("user-edit-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target;
  const changes = {};
  if (f.password.value) changes.password = f.password.value;
  if (f.role.value) changes.role = f.role.value;
  if (f.student_number.value) changes.student_number = f.student_number.value;
  try {
    await api("/users/" + f.id.value, { method: "PATCH", json: changes });
    showMessage("User " + f.id.value + " updated.");
    f.reset();
    await loadUsers();
  } catch (err) { showMessage(err.message, true); }
});