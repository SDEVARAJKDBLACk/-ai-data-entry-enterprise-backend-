# Python version
FROM python:3.11-slim

# System level-la thevaiyana libraries (Tesseract OCR mattrum GCC compiler)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    gcc \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requirements-ai copy panni install pannuvom
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Spacy model-ai build appovae download panniduvom
RUN python -m spacy download en_core_web_sm

# Ella files-aiyum copy pannuvom
COPY . .

EXPOSE 8501

# App-ai run panna command
CMD ["streamlit", "run", "main.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
