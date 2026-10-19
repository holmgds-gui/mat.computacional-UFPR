FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY dados/ ./dados/
COPY scripts/ ./scripts/
COPY disciplinas/ ./disciplinas/
COPY semestres/ ./semestres/
COPY app/ ./app/
COPY README.md ./README.md

EXPOSE 8080

CMD ["python", "app/servidor.py"]
