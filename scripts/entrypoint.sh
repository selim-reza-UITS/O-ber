#!/bin/sh

set -e

# Wait for database to be ready using Python
echo "Waiting for database to be ready..."
python << 'EOF'
import os
import sys
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src._config.settings.local')

max_retries = 30
retries = 0

while retries < max_retries:
    try:
        django.setup()
        from django.db import connection
        connection.ensure_connection()
        print("Database is ready!")
        break
    except Exception as e:
        retries += 1
        if retries >= max_retries:
            print("Database failed to become ready")
            sys.exit(1)
        print(f"Database not ready (attempt {retries}/{max_retries}), waiting...")
        import time
        time.sleep(2)
EOF

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Creating superuser..."
python manage.py shell << 'SUPERUSER'
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@gmail.com').exists():
    User.objects.create_superuser(email='admin@gmail.com', password='123', full_name='Admin')
    print("Superuser created: admin@gmail.com")
else:
    print("Superuser already exists")
SUPERUSER

exec "$@"