FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mnemo ./mnemo
COPY slack_app ./slack_app
COPY launcher.py .

# Writable memory store location (the /app dir isn't writable for the Space user).
ENV MNEMO_DATA_DIR=/tmp/mnemo_data
ENV PORT=7860
EXPOSE 7860

CMD ["python", "-u", "launcher.py"]
