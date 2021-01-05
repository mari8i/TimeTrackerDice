FROM python:3.8.7-slim-buster

RUN apt update && apt install -y apache2 apache2-dev libpq-dev && apt -y clean
RUN pip install mod_wsgi

WORKDIR /app

RUN chown -R www-data:www-data /app

COPY . /app/

COPY docker/.env.docker ./.env
COPY docker/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh
RUN pip install -r requirements.txt

EXPOSE 8000

RUN mkdir /app-data/
RUN chown www-data:www-data /app-data

USER www-data

ENTRYPOINT [ "./entrypoint.sh" ]
