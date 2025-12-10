# Python 3.10 का हल्का वर्जन (ताकि स्पेस कम ले)
FROM python:3.10-slim-buster

# वर्किंग डायरेक्टरी सेट करें
WORKDIR /app

# पहले requirements इंस्टॉल करें (ताकि बार-बार डाउनलोड न करना पड़े)
COPY requirements.txt requirements.txt
RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# बाकी सारा कोड कॉपी करें
COPY . .

# बोट स्टार्ट करने का कमांड
CMD ["python3", "main.py"]
