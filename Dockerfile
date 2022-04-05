FROM node:lts AS builder
WORKDIR /app

COPY package.json yarn.lock ./
RUN yarn --frozen-lockfile
COPY frontend ./frontend/
COPY vite.config.js tsconfig.json env.d.ts ./
RUN NODE_ENV=production yarn vite build

FROM python:3.10-slim-bullseye

# Configure system
WORKDIR /app


COPY Aptfile ./
RUN apt-get update && cat Aptfile | xargs apt-get install --yes --quiet --no-install-recommends 
RUN groupadd -r app && useradd --no-log-init -r -g app app
RUN mkdir -p /home/app && chown -R app /home/app
RUN mkdir -p /app && chown -R app /app
ENV POETRY_HOME=/usr/local
RUN curl -sSL https://install.python-poetry.org | python3 -
USER app
RUN poetry config virtualenvs.create false

# Install
COPY --chown=app:app pyproject.toml poetry.lock ./
RUN poetry install -n

COPY --chown=app:app . ./
COPY --chown=app --from=builder /app/vite ./vite
ENV PATH=$PATH:/home/app/.local/bin
RUN SECRET_KEY=dummy poetry run python manage.py collectstatic --noinput --clear

CMD ["bash", "-c", "gunicorn $GUNICORN_ARGS -b 0.0.0.0:${PORT:-80} app.wsgi"]
