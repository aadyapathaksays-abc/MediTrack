/* MediTrack front end: plain JavaScript, one function per page. */
const $ = s => document.querySelector(s);
const main = $("#main");
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const iso = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
const addDays = (s, n) => { const d = new Date(s + "T00:00"); d.setDate(d.getDate() + n); return iso(d); };
const t12 = t => new Date("2000-01-01T" + t).toLocaleTimeString([], {hour: "numeric", minute: "2-digit"});
const dLabel = s => new Date(s + "T00:00").toLocaleDateString([], {weekday: "short", day: "numeric", month: "short", year: "numeric"});
const pct = (a, b) => b ? Math.round(a / b * 100) : 0;
const today = () => iso(new Date());
const cap = s => s[0].toUpperCase() + s.slice(1);

async function api(url, method = "GET", body) {
  const r = await fetch("/api" + url, {method, headers: {"Content-Type": "application/json"}, body: body ? JSON.stringify(body) : undefined});
  const d = await r.json();
  if (!r.ok) throw new Error(d.error || "Something went wrong.");
  return d;
}

const ICONS = {
  dashboard: "M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z",
  medicines: "M10.5 20.5l10-10a4.95 4.95 0 00-7-7l-10 10a4.95 4.95 0 007 7zM8.5 8.5l7 7",
  reminders: "M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 01-3.4 0",
  history: "M3 12a9 9 0 109-9 9 9 0 00-6.7 3L3 8M3 3v5h5M12 7v5l3 2",
  calendar: "M3 5h18v16H3zM3 10h18M8 3v4M16 3v4",
  family: "M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2M9 11a4 4 0 100-8 4 4 0 000 8M22 21v-2a4 4 0 00-3-3.9M16 3.1a4 4 0 010 7.8"
};
const PAGES = [["dashboard","Dashboard"],["medicines","My Medicines"],["reminders","Reminders"],["history","Medication History"],["calendar","Calendar"],["family","Family Profiles"]];

let profile = +localStorage.pid || 1, chart, cal = {y: new Date().getFullYear(), m: new Date().getMonth(), sel: null}, hist = {mode: "day", date: today()};

/* ---------- shared pieces ---------- */
function doseRow(d, actions = true, showDate = false) {
  const btns = actions && (d.status === "upcoming" || d.status === "missed")
    ? `<button class="btn sm ok" onclick="mark(${d.id},'taken')">Mark as taken</button><button class="btn sm" onclick="mark(${d.id},'skipped')">Mark as skipped</button>` : "";
  return `<div class="item"><div class="time">${showDate ? dLabel(d.date) + "<br>" : ""}${t12(d.time)}</div>
    <div class="info"><b>${esc(d.name)}</b><span class="muted">${esc(d.dosage)}${d.instructions ? " · " + esc(d.instructions) : ""}</span></div>
    <span class="badge s-${d.status}">${cap(d.status)}</span>${btns}</div>`;
}
window.mark = async (id, status) => { await api("/doses/" + id, "POST", {status}); render(); };

/* ---------- pages ---------- */
async function dashboard() {
  const s = await api("/dashboard?profile=" + profile);
  const stat = (n, l) => `<div class="card stat"><b>${n}</b><span>${l}</span></div>`;
  main.innerHTML = `<div class="top"><h1>Dashboard</h1><button class="btn primary" onclick="openForm()">+ Add medicine</button></div>
    <section class="stats">${stat(s.active, "Active medicines")}${stat(s.today_total, "Doses scheduled today")}${stat(s.today_done, "Doses completed today")}${stat(s.today_pending, "Pending doses")}</section>
    <section class="grid2">
      <div class="card"><h2>Weekly adherence</h2><p class="big">${s.adherence}%</p><p class="muted">Taken doses out of all scheduled doses in the last 7 days.</p><div style="height:220px"><canvas id="ch"></canvas></div></div>
      <div class="card"><h2>Upcoming reminders</h2>${s.upcoming.length ? s.upcoming.map(u => `<div class="item"><div class="time">${t12(u.time)}</div><div class="info"><b>${esc(u.name)}</b><span class="muted">${esc(u.dosage)}</span></div></div>`).join("") : '<p class="empty">No more doses due today.</p>'}</div>
    </section>`;
  if (chart) chart.destroy();
  chart = new Chart($("#ch"), {type: "bar", data: {labels: s.week.map(w => w.label), datasets: [{label: "Adherence %", data: s.week.map(w => w.pct), backgroundColor: "#4f8fd8", borderRadius: 6}]},
    options: {maintainAspectRatio: false, plugins: {legend: {display: false}}, scales: {y: {min: 0, max: 100}}}});
}

async function medicines() {
  const ms = await api("/medicines?profile=" + profile), t = today();
  window._meds = ms;
  const tag = m => m.end_date < t ? '<span class="badge s-skipped">Ended</span>' : m.start_date > t ? '<span class="badge s-upcoming">Starts later</span>' : '<span class="badge s-taken">Active</span>';
  main.innerHTML = `<div class="top"><h1>My Medicines</h1><button class="btn primary" onclick="openForm()">+ Add medicine</button></div>
    <div class="card list">${ms.length ? ms.map(m => `<div class="item"><div class="info"><b>${esc(m.name)}</b>
      <span class="muted">${esc(m.dosage)} · ${m.times.map(t12).join(", ")} · ${dLabel(m.start_date)} to ${dLabel(m.end_date)}${m.instructions ? " · " + esc(m.instructions) : ""}</span></div>
      ${tag(m)}<button class="btn sm" onclick="openForm(${m.id})">Edit</button><button class="btn sm danger" onclick="delMed(${m.id})">Delete</button></div>`).join("") : '<p class="empty">No medicines yet. Add one to start tracking.</p>'}</div>`;
}
window.delMed = async id => { if (confirm("Delete this medicine and all its dose records?")) { await api("/medicines/" + id, "DELETE"); render(); } };

async function reminders() {
  const ds = await api(`/doses?profile=${profile}&start=${today()}&end=${today()}`);
  const perm = "Notification" in window ? Notification.permission : "unsupported";
  const note = perm === "granted" ? "" : perm === "default"
    ? `<div class="notice"><span>Turn on browser notifications to get a reminder at each dose time.</span><button class="btn primary sm" onclick="askPerm()">Enable notifications</button></div>`
    : `<div class="notice">Notifications are ${perm === "denied" ? "blocked in your browser settings" : "not supported in this browser"}. Reminders still appear on this page.</div>`;
  main.innerHTML = `<div class="top"><h1>Today's reminders</h1></div>${note}
    <div class="card list">${ds.length ? ds.map(d => doseRow(d)).join("") : '<p class="empty">No doses scheduled today.</p>'}</div>`;
}
window.askPerm = async () => { await Notification.requestPermission(); render(); };

async function history() {
  const start = hist.mode === "day" ? hist.date : addDays(hist.date, -6);
  const ds = await api(`/doses?profile=${profile}&start=${start}&end=${hist.date}`);
  const taken = ds.filter(d => d.status === "taken").length;
  main.innerHTML = `<div class="top"><h1>Medication History</h1></div>
    <div class="tabs"><button class="btn ${hist.mode === "day" ? "on" : ""}" onclick="setHist('day')">Daily</button><button class="btn ${hist.mode === "week" ? "on" : ""}" onclick="setHist('week')">Weekly</button>
      <input type="date" value="${hist.date}" max="${today()}" onchange="hist.date=this.value||today();render()" aria-label="Date">
      <span class="muted">${hist.mode === "day" ? "" : "7 days ending on this date"}</span></div>
    <section class="stats"><div class="card stat"><b>${pct(taken, ds.length)}%</b><span>Adherence (${taken} of ${ds.length} doses taken)</span></div></section>
    <div class="card table-wrap"><table><tr><th>Date</th><th>Time</th><th>Medicine</th><th>Dosage</th><th>Status</th></tr>
      ${ds.map(d => `<tr><td>${dLabel(d.date)}</td><td>${t12(d.time)}</td><td>${esc(d.name)}</td><td>${esc(d.dosage)}</td><td><span class="badge s-${d.status}">${cap(d.status)}</span></td></tr>`).join("") || '<tr><td colspan="5" class="empty">No doses in this period.</td></tr>'}</table></div>`;
}
window.setHist = m => { hist.mode = m; render(); };

async function calendar() {
  const {y, m} = cal, n = new Date(y, m + 1, 0).getDate(), lead = new Date(y, m, 1).getDay();
  const ds = await api(`/doses?profile=${profile}&start=${iso(new Date(y, m, 1))}&end=${iso(new Date(y, m, n))}`);
  const by = {}; ds.forEach(d => (by[d.date] ??= []).push(d));
  let cells = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"].map(d => `<div class="dow">${d}</div>`).join("") + '<div class="day blank"></div>'.repeat(lead);
  for (let i = 1; i <= n; i++) {
    const k = iso(new Date(y, m, i)), l = by[k] || [], c = !l.length ? "" : l.some(d => d.status === "missed") ? "missed" : l.some(d => d.status === "upcoming") ? "upcoming" : l.every(d => d.status === "taken") ? "taken" : "skipped";
    cells += `<button class="day ${c} ${cal.sel === k ? "sel" : ""}" onclick="cal.sel='${k}';render()">${i}${l.length ? `<small>${l.filter(d => d.status === "taken").length}/${l.length}</small>` : ""}</button>`;
  }
  const sel = cal.sel && by[cal.sel] || [];
  main.innerHTML = `<div class="top"><h1>${new Date(y, m).toLocaleDateString([], {month: "long", year: "numeric"})}</h1>
    <div><button class="btn" onclick="moveCal(-1)" aria-label="Previous month">‹</button> <button class="btn" onclick="moveCal(1)" aria-label="Next month">›</button></div></div>
    <div class="card"><div class="cal">${cells}</div>
    <div class="legend"><span class="badge s-taken">All taken</span><span class="badge s-upcoming">Upcoming</span><span class="badge s-missed">Missed</span><span class="badge s-skipped">Skipped</span><span>Numbers show doses taken / scheduled</span></div></div>
    ${cal.sel ? `<div class="card list" style="margin-top:14px"><h2>${dLabel(cal.sel)}</h2>${sel.length ? sel.map(d => doseRow(d, false)).join("") : '<p class="empty">No doses on this day.</p>'}</div>` : ""}`;
}
window.moveCal = n => { cal.m += n; if (cal.m < 0) { cal.m = 11; cal.y--; } if (cal.m > 11) { cal.m = 0; cal.y++; } cal.sel = null; render(); };

async function family() {
  const ps = await api("/profiles");
  main.innerHTML = `<div class="top"><h1>Family Profiles</h1></div>
    <div class="card" style="margin-bottom:14px"><form id="pf" class="row"><input id="pname" placeholder="Family member's name" required aria-label="Name"><button class="btn primary">Add profile</button></form></div>
    <div class="card list">${ps.map(p => `<div class="item"><div class="info"><b>${esc(p.name)}</b><span class="muted">${p.taken} completed · ${p.pending} pending · ${p.missed} missed</span></div>
      ${p.id === profile ? '<span class="badge s-taken">Viewing</span>' : `<button class="btn sm" onclick="switchTo(${p.id})">View schedule</button>`}</div>`).join("")}</div>`;
  $("#pf").onsubmit = async e => { e.preventDefault(); await api("/profiles", "POST", {name: $("#pname").value}); await loadProfiles(); render(); };
}
window.switchTo = id => { profile = id; localStorage.pid = id; $("#profile").value = id; location.hash = "#dashboard"; };

const views = {dashboard, medicines, reminders, history, calendar, family};

/* ---------- navigation ---------- */
function render() {
  const v = location.hash.slice(1) in views ? location.hash.slice(1) : "dashboard";
  $("#nav").innerHTML = PAGES.map(([k, l]) => `<a href="#${k}" class="${k === v ? "on" : ""}"><svg class="ic" viewBox="0 0 24 24"><path d="${ICONS[k]}"/></svg>${l}</a>`).join("");
  return views[v]().catch(e => main.innerHTML = `<p class="err">${esc(e.message)}</p>`);
}
async function loadProfiles() {
  const ps = await api("/profiles");
  if (!ps.some(p => p.id === profile)) profile = ps[0].id;
  $("#profile").innerHTML = ps.map(p => `<option value="${p.id}">${esc(p.name)}</option>`).join("");
  $("#profile").value = profile;
}
$("#profile").onchange = e => { profile = +e.target.value; localStorage.pid = profile; render(); };
window.addEventListener("hashchange", render);

/* ---------- add / edit medicine form ---------- */
const DEFAULT_TIMES = {1: ["09:00"], 2: ["09:00", "21:00"], 3: ["08:00", "14:00", "20:00"]};
function drawTimes(times) {
  $("#f_times").innerHTML = times.map((t, i) => `<label>Dose ${i + 1} time<input type="time" class="ft" value="${t}" required></label>`).join("");
}
$("#f_freq").onchange = () => drawTimes(DEFAULT_TIMES[$("#f_freq").value]);
$("#f_inst").onchange = () => { $("#f_custom").hidden = $("#f_inst").value !== "custom"; };
$("#addBtn").onclick = () => openForm();
$("#cancel").onclick = () => $("#dlg").close();
let editId = null;
window.openForm = id => {
  const m = id ? window._meds.find(x => x.id === id) : null;
  editId = id || null;
  $("#dlgTitle").textContent = m ? "Edit medicine" : "Add medicine";
  $("#f_name").value = m?.name || ""; $("#f_dosage").value = m?.dosage || "";
  $("#f_freq").value = m?.frequency || 1; drawTimes(m?.times || DEFAULT_TIMES[1]);
  $("#f_start").value = m?.start_date || today(); $("#f_end").value = m?.end_date || addDays(today(), 10);
  const inst = m?.instructions || "", preset = ["Before food", "After food", "With food"].includes(inst);
  $("#f_inst").value = !inst ? "" : preset ? inst : "custom";
  $("#f_custom").hidden = $("#f_inst").value !== "custom"; $("#f_custom").value = !preset ? inst : "";
  $("#f_err").textContent = ""; $("#dlg").showModal();
};
$("#form").onsubmit = async e => {
  e.preventDefault();
  const v = $("#f_inst").value;
  const body = {profile_id: profile, name: $("#f_name").value, dosage: $("#f_dosage").value, frequency: +$("#f_freq").value,
    times: [...document.querySelectorAll(".ft")].map(i => i.value), start_date: $("#f_start").value, end_date: $("#f_end").value,
    instructions: v === "custom" ? $("#f_custom").value : v};
  try {
    await (editId ? api("/medicines/" + editId, "PUT", body) : api("/medicines", "POST", body));
    $("#dlg").close(); render();
  } catch (err) { $("#f_err").textContent = err.message; }
};

/* ---------- browser notifications (work only while this page is open) ---------- */
const notified = new Set(JSON.parse(localStorage.notified || "[]"));
async function checkNotify() {
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  const now = new Date(), hm = now.toTimeString().slice(0, 5), ago = new Date(now - 5 * 60000).toTimeString().slice(0, 5);
  const ds = await api(`/doses?profile=${profile}&start=${today()}&end=${today()}`);
  ds.filter(d => ["upcoming", "missed"].includes(d.status) && d.time <= hm && d.time >= ago && !notified.has(d.id)).forEach(d => {
    new Notification("Time for " + d.name, {body: `${d.dosage}${d.instructions ? " · " + d.instructions : ""}`});
    notified.add(d.id);
  });
  localStorage.notified = JSON.stringify([...notified].slice(-200));
}
setInterval(checkNotify, 20000);
setInterval(() => { if (!$("#dlg").open && ["reminders", "dashboard"].includes(location.hash.slice(1) || "dashboard")) render(); }, 60000);

loadProfiles().then(render);
