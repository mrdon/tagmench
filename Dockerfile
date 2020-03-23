FROM python:3.8-slim

ENV PYTHONUNBUFFERED=1

RUN pip install textblob && python -m textblob.download_corpora

COPY src/alembic/requirements.txt /alembic/requirements.txt

RUN pip install -U pip
RUN python -m venv /alembic/venv \
    && /alembic/venv/bin/pip install -qq -r /alembic/requirements.txt

WORKDIR /app


COPY requirements.txt .
RUN pip install -r requirements.txt
RUN python -m textblob.download_corpora


COPY src/alembic.ini /
COPY src/alembic /alembic
COPY src /app
COPY src/dokku/CHECKS /app/CHECKS
COPY Procfile /app
COPY bin /app/bin


#
# ARG REVISION_HASH
# ENV REVISION_HASH ${REVISION_HASH}
# RUN echo "REVISION_HASH '$REVISION_HASH'"

EXPOSE 8080/tcp

ENV QUART_APP=/app/tagmench/app.py

CMD ["bin/run-web.sh"]
