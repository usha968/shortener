FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
COPY worker worker
RUN useradd -r app && chown -R app /srv
USER app
EXPOSE 8000
# FORWARDED_ALLOW_IPS (set in compose) tells uvicorn which proxies to trust for X-Forwarded-For.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
