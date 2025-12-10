# हम 'slim' की जगह फुल वर्शन यूज़ करेंगे (इसमें gcc कंपाइलर होता है)
FROM python:3.10

# वर्किंग डायरेक्टरी सेट करें
WORKDIR /app

# पहले requirements इंस्टॉल करें
COPY requirements.txt requirements.txt
RUN pip3 install --upgrade pip
RUN pip3 install --no-cache-dir -r requirements.txt

# बाकी कोड कॉपी करें
COPY . .

# बोट स्टार्ट करें
CMD ["python3", "main.py"]
