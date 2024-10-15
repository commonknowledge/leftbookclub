# Left Book Club

### Using VS Code development containers

0. (Check that VSCode has the right python interpreter selected, by comparing it to the path in `poetry run python -c "import sysconfig; print(sysconfig.get_paths()['scripts'])"`. You can see this in the bottom bar of editor UI)
1. [Generate a repository](https://github.com/commonknowledge/groundwork-starter-template/generate) from this template
2. In VSCode, run the command 'Clone Repository in Remote Container Volume' and select your new repository.
3. Wait for dependencies to install
4. Hit `F5` (or navigate to _Run & Debug_ and launch the _Start App_ configuration)

- If you are receiving errors like `No module named 'django'`, Open the command palette, select `> Python: Select Interpreter` and select the `Poetry`-installed python binary

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
- When you first set up, you should sync Stripe to the local database:

  ```
  poetry run python manage.py djstripe_sync_models Product Subscription Coupon
  ```

- And sync Shopify products:

  ```
  poetry run python manage.py sync_shopify_products
  ```

## Application stack

- [Django](https://www.djangoproject.com/)
- [Django Rest Framework](https://groundwork.commonknowledge.coop)
- [Groundwork](https://groundwork.commonknowledge.coop)

## Frontend stack

- [Stimulus](https://stimulus.hotwired.dev/)
- [Turbo](https://turbo.hotwired.dev/)
- [Bootstrap](https://groundwork.commonknowledge.coop)

## Development stack

- [Poetry](https://python-poetry.org/) for python dependencies
- [Vite](https://vitejs.dev/) for frontend build pipeline

## Deployment & CI stack

- VSCode Development Containers
- Github Actions
- Docker

## Render, our web host

- Render allows you to automatically deploy from a GitHub repository. To enable deployments, manually create the required apps on Render:
  - Create a new web service and link it to the GitHub repository
  - Create a new background worker and link it to the GitHub repository
  - Create a new postgres database. Render will create connection variables for you including an external database url
  - Add the new postgres database url to the environment variables in the web service: DATABASE_URL=(Render's External Database URL). These are found in the environment tab in the Render UI
  - Add the new postgres database url to the environment variables in the background worker: DATABASE_URL=(Render's External Database URL)
  - You can optionally repeat this process for a staging environment
- Set other environment secrets in the environment tab
  - Contact jan@commonknowledge.coop for all required env variables for the Left Book Club's instance, or see below for a general outline
- After the first deploy has completed, you can acesss the shell tab in the Render UI to enter the app and run set up commands, etc.

  - Use `poetry run ...` to access the python environment

    - Run `cd app` to enter the project root
    - E.g. `poetry run python manage.py createsuperuser`

## OAuth 2.0 provider details

The LBC app can be configured as an OAuth 2.0 provider, to provide authentication to third party systems like Circle.so.

How to get this going:

- You must generate an RSA private key and add it to base.py where `OIDC_RSA_PRIVATE_KEY` is specified.

  In production add `OIDC_RSA_PRIVATE_KEY` to the environment variables in Render

- From the Django admin panel, [create an OAuth2 application](http://localhost:8000/django/oauth2_provider/application) with credentials like this:

  ```
  {
    "id" : 1,
    "client_type" : "public",
    "updated" : "2022-06-15 19:32:04.045699+00",
    "user_id" : null,
    "redirect_uris" : "http:\/\/localhost:3000\/api\/auth\/callback http:\/\/localhost:3000\/api\/auth\/callback\/lbc http:\/\/localhost:3000\/api\/auth\/lbc\/callback",
    "created" : "2022-06-15 18:44:48.781143+00",
    "client_id" : "4AGN48TesXUV3I1pYnQY3t4rwrnFK7ZpazMN70oy",
    "client_secret" : "bcrypt_sha256$$2b$12$8T92Eh3RkEIjQxig7rf4jebRiIPKfmuzEpxefBFSEP9cNg2\/bpk5S",
    "skip_authorization" : false,
    "algorithm" : "RS256",
    "name" : "AuthCode",
    "authorization_grant_type" : "authorization-code"
  }
  ```

- Configure the client to use this provider application:
  ```
  {
    id: "lbc",
    name: "Left Book Club",
    type: "oauth",
    checks: ["pkce"],
    // idToken: true,
    wellKnown: "http://localhost:8000/o/.well-known/openid-configuration/",
    // authorization: "http://localhost:8000/o/authorize/",
    // token: "http://localhost:8000/o/token/",
    // userinfo: "http://localhost:8000/o/user/me/",
    clientId: "4AGN48TesXUV3I1pYnQY3t4rwrnFK7ZpazMN70oy",
    clientSecret: "...",
    profile(profile) {
      return {
        id: profile.id,
        name: profile.name,
        email: profile.email,
      }
    },
  }
  ```

We used https://github.com/nextauthjs/next-auth-example/ to test this implementation.

### Setting up database

#### Render

Connect to the database by running `psql (Render's External Database URL)` and run all the CREATE EXTENSION commands:

```
-- Enable PostGIS (as of 3.0 contains just geometry/geography)
CREATE EXTENSION postgis;
-- enable raster support (for 3+)
CREATE EXTENSION postgis_raster;
-- Enable Topology
CREATE EXTENSION postgis_topology;
-- Enable PostGIS Advanced 3D
-- and other geoprocessing algorithms
-- sfcgal not available with all distributions
CREATE EXTENSION postgis_sfcgal;
-- fuzzy matching needed for Tiger
CREATE EXTENSION fuzzystrmatch;
-- rule based standardizer
CREATE EXTENSION address_standardizer;
-- example rule data set
CREATE EXTENSION address_standardizer_data_us;
-- Enable US Tiger Geocoder
CREATE EXTENSION postgis_tiger_geocoder;
```

### Secrets

#### Staging

```js
DATABASE_URL;
SECRET_KEY; // random key
BASE_URL; // set this to the URL of your staging site
STRIPE_LIVE_MODE = False;
STRIPE_WEBHOOK_SECRET; // signing secret from https://dashboard.stripe.com/test/webhooks/we_1KlUZ2KYdS0VccAEF1CWol1Q
STRIPE_TEST_SECRET_KEY; // API key section: https://dashboard.stripe.com/test/apikeys
STRIPE_TEST_PUBLIC_KEY; // API key section: https://dashboard.stripe.com/test/apikeys
```

#### Production

Contact jan@commonknowledge.coop for an up to date list of env variables

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
//From https://left-book-club-shop.myshopify.com/admin/apps/private/349095133417
SHOPIFY_APP_API_SECRET: "...",
SHOPIFY_PRIVATE_APP_PASSWORD: "...",
//Manually specified
STRIPE_LIVE_MODE: "False" // or True
SECRET_KEY: "..."
// From https://render.com
BASE_URL: "https://...onrender.com"
//From Stripe
STRIPE_TEST_PUBLIC_KEY: "..."
STRIPE_TEST_SECRET_KEY: "..."
STRIPE_WEBHOOK_SECRET: "..."
```
