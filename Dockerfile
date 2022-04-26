FROM nikolaik/python-nodejs:python3.9-nodejs18-bullseye
WORKDIR /app

# OS deps
COPY Aptfile ./
RUN apt-get update && cat Aptfile | xargs apt-get install --yes --quiet --no-install-recommends 
RUN groupadd -r app && useradd --no-log-init -r -g app app
RUN mkdir -p /home/app && chown -R app /home/app
RUN mkdir -p /app && chown -R app /app
ENV POETRY_HOME=/usr/local
RUN curl -sSL https://install.python-poetry.org | python3 -
USER app
RUN poetry config virtualenvs.create true
RUN poetry config virtualenvs.in-project true

# Python deps
COPY --chown=app:app pyproject.toml poetry.lock ./
RUN poetry install -n

# Frontend deps
COPY package.json yarn.lock ./
RUN yarn --frozen-lockfile

# Remaining project files
COPY --chown=app:app . ./

# Frontend build
# with files available for purgecss
RUN NODE_ENV=production yarn vite build

# Django prep
ENV DJANGO_SETTINGS_MODULE=app.settings.production
ENV PATH=$PATH:/home/app/.local/bin
RUN SECRET_KEY=dummy poetry run python manage.py collectstatic --noinput --clear

CMD ["bash", "-c", "poetry run gunicorn $GUNICORN_ARGS -b 0.0.0.0:${PORT:-80} app.wsgi"]
