FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8765

WORKDIR /app

COPY config ./config
COPY scripts ./scripts
COPY data/sample/comp_catalog.csv ./data/sample/comp_catalog.csv

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:' + __import__('os').environ.get('PORT', '8765') + '/healthz', timeout=2)"

CMD ["sh", "-c", "python scripts/manager_app.py --host 0.0.0.0 --port ${PORT}"]
