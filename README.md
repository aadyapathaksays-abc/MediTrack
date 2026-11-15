# MediTrack — Medicine Reminder & Tracker

A small Flask + SQLite web application suitable as a student project starter.

## Features
- Add and remove medicines from the active schedule
- Store dosage, reminder time, dates, instructions and stock
- Mark a medicine as taken or skipped
- View dose activity history
- Low-stock indicator
- Dashboard summary
- SQLite database created automatically

## Run locally

1. Install Python 3.10 or newer.
2. Open a terminal in this project folder.
3. Create and activate a virtual environment (recommended).
4. Install dependencies:

   `pip install -r requirements.txt`

5. Start the app:

   `python app.py`

6. Open `http://127.0.0.1:5000` in your browser.

## Deploying for a shareable link

This project includes a `Procfile` for common Python hosting platforms. Create a new web service from this folder/repository, set the build/install command to `pip install -r requirements.txt`, and use `gunicorn app:app` as the start command. Follow the host's current instructions for persistent storage and environment variables.

SQLite is suitable for a local demo. For a multi-user public deployment, use a production database, authentication, access controls, HTTPS, backups and persistent storage before entering any real personal or health information. Set a secure `SECRET_KEY` environment variable before deployment.

## Important limitations

- This is a demonstration project, not a medical device.
- The app does not send background push/SMS reminders. It stores the schedule and displays it on the dashboard; actual reminders need a notification service or scheduled client.
- Dose logging is a simple demo: one status entry per medicine per calendar day.
- The app has no login or multi-user separation yet.
- Do not use real patient information in this demo.
- Never change a prescription based on this app. Follow the prescribing clinician's instructions.
