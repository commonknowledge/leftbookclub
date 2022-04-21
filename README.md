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

### Troubleshooting

#### `ModuleNotFoundError: No module named 'django'`

- Manually run `poetry install`
- From the VSCode command pallete, "select Python interpreter" and select the virtualenv binary of Python

#### Precommit not installed

- If you get git errors about `pre_commit`, [install `pre-commit`](https://formulae.brew.sh/formula/pre-commit) outside the devcontainer and run `pre-commit install` to re-configure the git environment.

#### Precommit: icu4c (not found)

For errors like this:

```
dyld: Library not loaded: /usr/local/opt/icu4c/lib/libicui18n.62.dylib
  Referenced from: /usr/local/bin/php
  Reason: image not found
```

... clean up your brew installs (see https://stackoverflow.com/a/54873233/1053937)

### Developer set up

- `cd app` to enter the right area
- Run `poetry run python manage.py createsuperuser` to set up an admin user
- To get stripe webhooks forwarded to the local app, [follow these instructions](https://stripe.com/docs/stripe-vscode#webhooks)
- When you first set up, you should sync Stripe to the local database:

  ```
  poetry run python manage.py djstripe_sync_models Price Product Customer Subscription Plan Coupon
  ```

- And sync Shopify products:

  ```
  poetry run python manage.py sync_shopify_products
  ```

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

## Fly.io, our web host

- `fly launch` to set up the app, ignoring Django detection
- If a database hasn't been automatically created through the above, `flyctl postgres create`
- `flyctl postgres attach --app <app-name> --postgres-app <postgres-app-name>` to link the two
- Set environment secrets with `flyctl secrets set KEY="VALUE" KEY2="VALUE2" ...`
- Deploy the app via `flyctl deploy` or the github workflows configured in this repo
- Then use `flyctl ssh console` to enter the app and run set up commands, etc.

### Secrets

```js
DJANGO_SETTINGS_MODULE: "app.settings.production",
// From https://cloud.digitalocean.com/account/api/tokens?i=e4951b
// # like `leftbookclub`
AWS_STORAGE_BUCKET_NAME: "leftbookclub",
AWS_S3_REGION_NAME: "fra1",
// # like `https://fra1.digitaloceanspaces.com`
AWS_S3_ENDPOINT_URL: "https://fra1.digitaloceanspaces.com",
AWS_ACCESS_KEY_ID: "...",
AWS_SECRET_ACCESS_KEY: "...",
MEDIA_URL: "https://fra1.digitaloceanspaces.com/leftbookclub/",
//From Mailjet
MAILJET_API_KEY: "...",
MAILJET_SECRET_KEY: "...",
//From https://mjml.io
MJML_APPLICATION_ID: "...",
MJML_SECRET_KEY: "...",
//From https://left-book-club-shop.myshopify.com/admin/apps/private/349095133417
SHOPIFY_APP_API_SECRET: "...",
SHOPIFY_PRIVATE_APP_PASSWORD: "...",
//Manually specified
STRIPE_LIVE_MODE: "False" // or True
SECRET_KEY: "..."
// From https://fly.io
BASE_URL: "https://...fly.dev"
//From Stripe
STRIPE_TEST_PUBLIC_KEY: "..."
STRIPE_TEST_SECRET_KEY: "..."
STRIPE_WEBHOOK_SECRET: "..."
DJSTRIPE_WEBHOOK_SECRET: "..."
```
