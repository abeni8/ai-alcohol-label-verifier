# Uses the included, browser-tested static React build. No Node runtime is needed.
# After editing frontend/src, rebuild frontend/dist before building this image.
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 reviewer
COPY --chown=reviewer:reviewer backend/app ./backend/app
COPY --chown=reviewer:reviewer frontend/dist ./frontend/dist
COPY --chown=reviewer:reviewer samples ./samples
COPY --chown=reviewer:reviewer scripts/run.py ./scripts/run.py
USER reviewer
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8000')+'/api/ready', timeout=3)"
CMD ["python", "scripts/run.py", "--host", "0.0.0.0"]
