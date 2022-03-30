# Groundwork Starter

A starter repository for [Groundwork](https://groundwork.commonknowledge.coop) projects.

## Quickstart:

### Using vscode development containers:

1. [Generate a repository](https://github.com/commonknowledge/groundwork-starter-template/generate) from this template
2. In VSCode, run the command 'Clone Repository in Remote Container Volume' and select your new repository.
3. Wait for dependencies to install
4. Hit `F5` (or navigate to _Run & Debug_ and launch the _Start App_ configuration)
  - If you are receiving errors like `No module named 'django'`, Open the command palette, select `> Python: Select Interpreter` and select the `Poetry`-installed python binary.
5. Navigate to http://localhost:8000
  
### Developer set up

- Run `python manage.py createsuperuser` to set up an admin user
- To get stripe webhooks forwarded to the local app, [follow these instructions](https://stripe.com/docs/stripe-vscode#webhooks)

## Application stack:

- [Django](https://www.djangoproject.com/)
- [Django Rest Framework](https://groundwork.commonknowledge.coop)
- [Groundwork](https://groundwork.commonknowledge.coop)

## Frontend stack:

- [Stimulus](https://stimulus.hotwired.dev/)
- [Turbo](https://turbo.hotwired.dev/)
- [Bootstrap](https://groundwork.commonknowledge.coop)

## Development stack:

- [Poetry](https://python-poetry.org/) for python dependencies
- [Vite](https://vitejs.dev/) for frontend build pipeline

## Deployment & CI stack:

- VSCode Development Containers
- Github Actions
- Docker
