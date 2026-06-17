# ---- frontend build stage ----
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- python build stage ----
FROM python:3.12-slim AS build
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- runtime stage ----
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --create-home appuser
WORKDIR /app
COPY --from=build /install /usr/local
COPY . .
COPY --from=frontend-build /frontend/dist ./frontend/dist
RUN python manage.py collectstatic --noinput
USER appuser
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
