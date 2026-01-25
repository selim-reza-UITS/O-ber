# O-ber Backend Deployment Guide

Follow these steps when you arrive at the office to set up the backend and verify it for your Flutter developer.

## 1. Pull Latest Code
```bash
git pull origin staging
```

## 2. Start Services (Database & Redis)
Ensure Docker is running, then start the support containers:
```bash
docker compose up -d --build
# If you don't have 'docker compose', use: docker-compose up -d --build
```

## 3. Apply New Migrations
We added fields for Stripe and Payment history. You must apply these to your office database.
```bash
# If running locally with venv:
source venv/bin/activate
python manage.py migrate

# OR if running everything inside Docker:
# docker compose exec web python manage.py migrate
```

## 4. Run System Check (Verification)
Ensure everything is wired up correctly:
```bash
python manage.py check
```
*(Should return "System check identified no issues")*

## 5. Verify API Accessibility
Check if the server is reachable at your IP (e.g., `10.10.13.22`).
```bash
# Start server (if not already running via Docker)
python manage.py runserver 0.0.0.0:8000
```
Then visit `http://10.10.13.22:8000/api/v1/platform/about-us/` in your browser. You should see a JSON response.

## 6. Handover to Flutter Dev
1.  **Share the Docs**: Send them the `FLUTTER_API_DOCS.md` file located in the root of the project.
2.  **Stripe Key**: Ensure they have the Stripe Publishable Key (from your `.env`).
3.  **Confirm Base URL**: Tell them to point their app to `http://10.10.13.22:8000/api/v1/` (or whatever IP your office machine has).

## Troubleshooting
- **Database Connection Error**: Make sure `docker compose up` is running.
- **Stripe Errors**: Check `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` in your `.env` file.
