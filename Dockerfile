FROM python:3-alpine
# hadolint ignore=DL3018

ENV PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  POETRY_VERSION=1.1.13
# trunk-ignore(hadolint/DL3018)
RUN apk add --no-cache build-base curl libffi-dev libxml2-dev libxslt-dev openssl-dev
WORKDIR /usr/src/app
COPY poetry.lock pyproject.toml ./
ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1
# hadolint ignore=DL3013
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi
COPY src/* .
ENV FLASK_APP=morning
ENV PYTHONUNBUFFERED=TRUE
EXPOSE 5000
CMD ["gunicorn", "morning:app", "-w", "2", "--threads", "2", "-b", "0.0.0.0:5000", "--access-logfile", "-"]
