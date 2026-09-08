FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY src/ ./src/
COPY tests/ ./tests/
COPY eval.py pytest.ini solve.sh instruction.md ./
RUN chmod +x solve.sh


ENTRYPOINT ["python"]
