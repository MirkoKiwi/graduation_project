FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libexpat1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .


# RUN pip install --no-cache-dir -r requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt


COPY . .

CMD ["python", "main.py"]