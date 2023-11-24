FROM nikolaik/python-nodejs:python3.9-nodejs18-bullseye
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
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

# Collect static so that templates are available for purging
ENV DJANGO_SETTINGS_MODULE=app.settings.production
ENV PATH=$PATH:/home/app/.local/bin
RUN SECRET_KEY=dummy poetry run python manage.py collectstatic --noinput --clear

# Frontend build
# with files available for purgecss
RUN NODE_ENV=production yarn vite build

# Rerun collect static to include the built files
RUN SECRET_KEY=dummy poetry run python manage.py collectstatic --noinput --clear

EXPOSE 8080

CMD ["bash", "-c", "poetry", "run", "gunicorn", "--bind", ":8080", "--workers", "2", "app.wsgi"]
