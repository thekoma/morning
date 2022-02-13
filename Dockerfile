FROM python:3-alpine
# hadolint ignore=DL3018
RUN apk add --no-cache build-base curl libffi-dev libxml2-dev libxslt-dev openssl-dev
WORKDIR /usr/src/app
COPY requirements.txt ./
ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1
# hadolint ignore=DL3013
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt
COPY src/* .
ENV FLASK_APP=morning
ENV PYTHONUNBUFFERED=TRUE
EXPOSE 5000
CMD ["gunicorn", "morning:app", "-w", "2", "--threads", "2", "-b", "0.0.0.0:5000", "--access-logfile", "-"]
