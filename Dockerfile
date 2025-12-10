FROM python:3.10-slim

WORKDIR /app

# Install dependencies (gcc और अन्य टूल्स के साथ)
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    musl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "main.py"]
