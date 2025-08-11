FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy core project first for dependency install
COPY pyproject.toml README.md /app/
COPY promptsan /app/promptsan

# Install project (provides promptsan and its deps)
RUN pip install --no-cache-dir .

# Copy example requirements for the API server
COPY examples/fastapi/requirements.txt /app/examples/fastapi/requirements.txt
RUN pip install --no-cache-dir -r /app/examples/fastapi/requirements.txt

# Copy the rest of the project (examples, configs)
COPY examples /app/examples

EXPOSE 9000

CMD ["uvicorn", "examples.fastapi.main:app", "--host", "0.0.0.0", "--port", "9000", "--workers", "1"]
