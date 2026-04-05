FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements_dashboard.txt .
RUN pip install --no-cache-dir -r requirements_dashboard.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "src/dashboard/dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]