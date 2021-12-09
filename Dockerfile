FROM ghcr.io/commonknowledge/do-app-baseimage-django-node:405a148156ab16f9f6cc177ea7d9141c0f4af419

# Install the project requirements and build.
COPY --chown=app:app .bin/install.sh Pipfile Pipfile.lock package.json yarn.lock .
RUN SKIP_MIGRATE=1 bash install.sh

# Copy the rest of the sources over
COPY --chown=app:app . .
ENV DJANGO_SETTINGS_MODULE=stopwatch.settings.production \
    NODE_ENV=production

RUN make build
