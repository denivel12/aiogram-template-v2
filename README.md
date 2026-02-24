# aiogram-template

This is a template for creating Telegram bots using the aiogram library.

#### ❗️ Read [HELP.md](HELP.md) if something is unclear ❗️

### Template uses:

* aiogram 3
* SQLAlchemy + Alembic
* PostgreSQL
* Redis
* Caddy Server
* Docker
* i18n (Project Fluent)
* uv

***

## Installation

### Step 1: Clone the repository

```shell
git clone https://github.com/andrew000/aiogram-template.git
cd aiogram-template
```

### Step 2: Install dependencies

1. Install [JUST](https://just.systems/man/en/introduction.html) to manage project commands.
2. Install [UV](https://docs.astral.sh/uv/) to manage your project.

```shell
# Create virtual environment using UV
uv venv --python=3.13

# Install dependencies
just sync
```

### Step 3: Create `.env` file

Create a `.env` file in the root of the project and fill it with the necessary data. Set `DEV=True`
for development mode.

```shell
cp .env.example .env
```

### Step 4: Deploy project

```shell
just up
```

### Step 5: Run migrations

Template already has initial migration. To apply it, run the following command:

```shell
just upgrade-revision head
```

### Step 6: Bot is ready and running

Bot is ready to use. You can check the logs using the following command:

```shell
docker compose logs -f
```

***

## Explanation

### Project structure

The project structure is as follows:

```
AIOGRAM-TEMPLATE
├───app (main application)
│   ├───bot (bot)
│   │   ├───errors (error handlers)
│   │   ├───filters (custom filters)
│   │   ├───handlers (event handlers)
│   │   ├───locales (localization files)
│   │   ├───main.py (bot entrypoint)
│   │   ├───middlewares (event middlewares)
│   │   ├───pyproject.toml (bot workspace configuration)
│   │   ├───settings.py (bot settings)
│   │   ├───storages (database storages)
│   │   └───utils (utility functions)
│   ├───migrations (alembic migrations)
│   │   ├───alembic.ini (alembic configuration)
│   │   ├───env.py (alembic environment)
│   │   ├───pyproject.toml (alembic workspace configuration)
│   │   └───versions (migration files)
├───caddy (Caddy web server)
├───psql (PostgreSQL database)
│   ├───data (database data)
│   └───db-init-script (database initialization script)
├───redis (Redis database)
│   └───data (redis data)
├───pyproject.toml (project configuration)
├───docker-compose.yml (docker-compose configuration)
├───.env.example (example environment file)
├───.pre-commit-config.yaml (pre-commit configuration)
└───Justfile (just commands)
```

The bot is located in the `app/bot` directory. The bot is divided into modules, each of which is
responsible for a
specific functionality. `handlers` are responsible for processing events, `middlewares` for
preprocessing events,
`storages` for declaring models and working with the database, `locales` for localization, `filters`
for own filters,
`errors` for error handling.

### Migrations

Migration files are located in the `app/migrations` directory.

❗️ It is recommended to create migrations files before you push your code to the repository.

❗️ Always check your migrations before apply them to the production database.

To create initial migration, check if your models imported in the
`app/bot/storages/psql/__init__.py` file and run the
following command:

```shell
just create-init-revision
```

To apply `head` migration, run the following command:

```shell
just upgrade-revision head
```

To apply specific migration, run the following command:

```shell
just upgrade-revision <revision_id>
```

`revision_id` - id of the migration in the `app/migrations/versions` directory. Initial migration id
is
`000000000000`.

To check current migration `revision_id` in the database, run the following command:

```shell
just current-revision
```

### Localization

The Bot supports localization. Localization files are located in the `app/bot/locales` directory.
The bot uses the
`aiogram-i18n` library for localization and `FTL-Extract` for extracting FTL-keys from the code.

To extract FTL-keys from the code, run the following command:

```shell
just extract-locales
```

After extracting FTL-keys, you can find new directories and files in the `app/bot/locales`
directory. To add or remove
locales for extraction, edit `Justfile`

I recommend to make a submodule from `app/bot/locales` directory. It will allow you to control
locales versions and
publish them (without code exposing) for translations help by other people.

### Pre-commit

The project uses pre-commit hooks. To install pre-commit hooks, run the following command:

```shell
uv run pre-commit install
```

### Docker

The project uses Docker for deployment. To build and run the bot in Docker, run the following
command:

```shell
just up
```

Yes, little command to run large project. It will build and run the bot, PostgreSQL, Redis, and
Caddy containers.

To gracefully stop the bot and remove containers, run the following command:

```shell
just down
```

### Caddy

The project uses Caddy as a web server. Caddy can automatically get and renew SSL certificates. To
configure Caddy, edit
the `Caddyfile` file in the `caddy` directory. `public` directory is used to store static files.

By default, Caddy is disabled in the `docker-compose.yml` file. To enable Caddy, uncomment the
`caddy` service in the
`docker-compose.yml` file.

### Webhooks

Bot may use webhooks. To enable webhooks, set `WEBHOOKS` environment variable to `True` in the
`.env` file. Also, set
`WEBHOOK_URL` and `WEBHOOK_SECRET_TOKEN` environment variables.

Don't forget to uncomment the `caddy` service in the `docker-compose.yml` file.

***

## Architecture & Key Decisions

### Middleware Dependency Injection

The template uses a middleware-based dependency injection pattern to provide database sessions,
Redis connections, and other dependencies to handlers. Understanding this flow is crucial for
extending the bot.

#### Data Flow Through Middlewares

When an update arrives from Telegram, it passes through the following middleware chain:

```
Update → DatabaseMiddleware → CheckChatMiddleware → CheckUserMiddleware → Handler
```

Each middleware can add data to the `data` dictionary, which is then available to subsequent
middlewares and the final handler.

#### Key Dependencies in `data` Dictionary

| Key | Source | Description |
|-----|--------|-------------|
| `session` | `DatabaseMiddleware` | SQLAlchemy `AsyncSession` for database operations |
| `db_pool` | `DatabaseMiddleware` | `async_sessionmaker` for creating new sessions |
| `redis` | `Dispatcher` | Redis client instance for caching |
| `settings` | `Dispatcher` | Bot settings instance |
| `user_model` | `CheckUserMiddleware` | Redis-cached user model (for private chats) |
| `user_settings` | `CheckUserMiddleware` | Redis-cached user settings |
| `chat_model` | `CheckChatMiddleware` | Redis-cached chat model (for groups/supergroups) |
| `chat_settings` | `CheckChatMiddleware` | Redis-cached chat settings |

#### Why `db_pool` and `session` Both Exist

- **`session`**: A single database session for the current request lifecycle. Use this for most
  database operations in handlers.

- **`db_pool`**: The session factory (`async_sessionmaker`). Use this when you need to create
  separate sessions with different transaction scopes, such as in background tasks or when
  you need independent transactions.

Example usage in a handler:

```python
from typing import TYPE_CHECKING
from aiogram.types import Message

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from redis.asyncio import Redis

async def my_handler(
    message: Message,
    session: AsyncSession,  # Provided by DatabaseMiddleware
    db_pool: async_sessionmaker[AsyncSession],  # Provided by DatabaseMiddleware
    redis: Redis,  # Provided by Dispatcher
) -> None:
    # Use session for simple operations
    result = await session.execute(select(User).where(User.id == message.from_user.id))
    
    # Use db_pool for separate transaction scope
    async with db_pool() as new_session:
        # This is a separate transaction
        await new_session.execute(...)
        await new_session.commit()
```

### Redis Caching Strategy

The template implements a two-layer caching strategy:

1. **Redis Cache (Fast)**: User and chat data is cached in Redis for quick access
2. **PostgreSQL (Persistent)**: Authoritative data storage

When `CheckUserMiddleware` or `CheckChatMiddleware` runs, they first check Redis for cached
data. If not found, they fetch from PostgreSQL and cache it in Redis. This reduces database
load and improves response times.

### Middleware Registration Order

The order of middleware registration in [`main.py`](app/bot/main.py) is important:

```python
# Outer middlewares run first (in order of registration)
dp.update.outer_middleware(DatabaseMiddleware(session_pool=session_pool))
dp.update.outer_middleware(CheckChatMiddleware())
dp.update.outer_middleware(CheckUserMiddleware())

# Inner middlewares run after outer middlewares
dp.message.middleware(ThrottlingMiddleware(redis))
dp.callback_query.middleware(ThrottlingMiddleware(redis))
```

- **Outer middlewares**: Run for all update types. Used for core functionality like database
  sessions and user/chat resolution.

- **Inner middlewares**: Run for specific event types (message, callback_query). Used for
  event-specific logic like throttling.

### Adding New Dependencies

To add a new dependency available to all handlers:

1. **Via Dispatcher** (recommended for single instances like clients):

   ```python
   dp = Dispatcher(
       storage=storage,
       my_client=my_client,  # Will be available as data["my_client"]
   )
   ```

2. **Via Middleware** (for per-request instances or complex logic):

   ```python
   class MyMiddleware(BaseMiddleware):
       def __init__(self, dependency):
           self.dependency = dependency
       
       async def __call__(self, handler, event, data):
           data["my_dependency"] = self.dependency
           return await handler(event, data)
   
   dp.update.outer_middleware(MyMiddleware(my_dependency))
   ```

### Demo Commands

The template includes demo commands to showcase the architecture:

- `/start` - Basic start command with localization
- `/help` - Shows help information
- `/info` - Displays user information from the database
- `/test` - Tests PostgreSQL and Redis connectivity
- `/language` - Changes user's language preference

These commands demonstrate:
- Dependency injection in handlers
- Database operations with SQLAlchemy
- Redis caching
- Localization with aiogram-i18n
- Keyboard builders and callback queries
