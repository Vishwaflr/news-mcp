from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# Import your models here
from app.models import *
from sqlmodel import SQLModel

target_metadata = SQLModel.metadata

# Protected tables that should never be auto-dropped
PROTECTED_TABLES = {
    'item_analysis',
    'analysis_runs',
    'analysis_run_items',
    'analysis_presets',
    'content_processing_logs',
    'feed_template_assignments'
}

# Tables to ignore completely (artifacts)
IGNORED_TABLES = {
    'basetablemodel'  # SQLModel artifact, will be dropped explicitly
}

def include_object(object, name, type_, reflected, compare_to):
    """
    Filter function for Alembic autogenerate.
    Prevents accidental drops of protected tables.
    """
    # Skip ignored tables entirely
    if type_ == "table" and name in IGNORED_TABLES:
        return False

    # Protect analysis tables from being dropped
    if type_ == "table" and compare_to is None and name in PROTECTED_TABLES:
        # Table exists in DB but not in metadata - don't drop!
        print(f"⚠️  Protected table '{name}' exists in DB but not in models - keeping it")
        return False

    # Allow all other operations
    return True

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
