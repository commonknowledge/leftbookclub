#!/bin/bash
poetry run python manage.py start_worker &
poetry run python manage.py start_cron_worker &
wait
