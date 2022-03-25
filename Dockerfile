FROM ghcr.io/commonknowledge/do-app-baseimage-django-node:234cc1a78abaa803dbdf0d228c73b562a530d8d1

# Install the project requirements and build.
COPY --chown=app:app Makefile pyproject.toml poetry.lock package.json yarn.lock .
RUN make install

# Copy the rest of the sources over
COPY --chown=app:app . .
ENV DJANGO_SETTINGS_MODULE=app.settings.production \
    NODE_ENV=production

RUN make build
