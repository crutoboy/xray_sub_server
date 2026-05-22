FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn==23.0.*

COPY . .

EXPOSE 2096

CMD ["gunicorn", "--workers=4", "--bind=0.0.0.0:2096", "wsgi:app"]