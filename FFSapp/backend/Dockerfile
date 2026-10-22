FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Docker ENV lines cannot carry trailing comments: listen on all interfaces
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
# Auto-reload during development (FLASK_ENV was removed in Flask 2.3)
ENV FLASK_DEBUG=1

EXPOSE 5000
CMD ["flask", "run"]
