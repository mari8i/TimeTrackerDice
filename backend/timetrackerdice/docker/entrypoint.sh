#!/bin/sh

SLEEP_TIME="${DB_WAIT_SLEEP_TIME:-10}"

echo "Waiting ${SLEEP_TIME} seconds for the DB to come up"
sleep "${SLEEP_TIME}"

python manage.py migrate
python manage.py collectstatic --no-input

mkdir -p /app-data/media/
chown -R "$MOD_WSGI_USER" /app-data/media/

exec mod_wsgi-express start-server \
     --log-to-terminal \
     --startup-log \
     --port 8000 \
     --url-alias /static /app-data/static \
     --url-alias /media /app-data/media \
     "timetrackerdice/wsgi.py"
