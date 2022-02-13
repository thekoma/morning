FROM python:3-alpine
RUN apk add --no-cache build-base curl libffi-dev libxml2-dev libxslt-dev rust
WORKDIR /usr/src/app
ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1
ENV CRYPTOGRAPHY_DONT_BUILD_CARGO=1
COPY requirements.txt ./
RUN pip install --upgrade pip; pip install --no-cache-dir -r requirements.txt
COPY . .
ENV FLASK_APP=morning
ENV PYTHONUNBUFFERED=TRUE
EXPOSE 5000

CMD ["gunicorn", "morning:app", "-w", "2", "--threads", "2", "-b", "0.0.0.0:5000", "--access-logfile", "-"]
