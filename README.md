# MediTrack – Medicine Reminder & Tracker

Flask + SQLite + plain HTML/CSS/JS + Chart.js.

## Run locally
1. Install Python 3.9+.
2. In this folder:
   ```
   pip install -r requirements.txt
   python app.py
   ```
3. Open http://127.0.0.1:5000

The SQLite database (`meditrack.db`) is created automatically on first run. Delete it to reset all data.
Chart.js and the font load from the internet (CDN), so connect to the internet for the chart to show.

## Files
- `app.py` – database tables, dose generation, REST API
- `static/index.html` – page shell and the add/edit form
- `static/style.css` – design
- `static/app.js` – one function per page (dashboard, medicines, reminders, history, calendar, family)

## How it works
- Dose records are created from each medicine's schedule (start date → today). A UNIQUE(medicine, date, time) rule prevents duplicates.
- A dose is **Upcoming** until its time passes; then it becomes **Missed** unless you mark it Taken/Skipped (you can still mark a missed dose later).
- Adherence = taken ÷ total scheduled × 100. Skipped and missed doses don't count as taken.
- Editing a medicine rebuilds its unconfirmed doses; Taken/Skipped history is kept. Deleting a medicine also deletes its doses.

## Notification limitations
Browser notifications work only while the MediTrack tab is open (it can be in the background) and after you click "Enable notifications" on the Reminders page. Browsers may delay timers in sleeping tabs, and notifications only cover the profile currently selected. True background alerts when the browser is closed would need a service worker with push, which is out of scope for Phase 1.

## Not included
Per the scope: no medical advice, interaction checks, inventory, payments, appointments, login, or profile deletion.
