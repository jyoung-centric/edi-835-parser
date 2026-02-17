"""Database connection configuration and factory."""

import os
import sys
from pathlib import Path
from typing import Dict
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import connection as Connection


def load_config() -> Dict[str, str]:
    """
    Load database configuration from .env file and environment variables.

    Environment variables override .env file values.

    Returns:
        Dict[str, str]: Configuration dictionary with DB credentials

    Raises:
        ValueError: If DB_PASSWORD is not set
    """
    if getattr(sys, 'frozen', False):
        # Bundled exe — load .env from the same directory as the exe
        load_dotenv(Path(sys.executable).parent / '.env')
    else:
        # Dev — load from cwd (existing behaviour)
        load_dotenv()

    config = {
        'DB_HOST': os.getenv('DB_HOST', 'botdb.prxdev.com'),
        'DB_PORT': os.getenv('DB_PORT', '5432'),
        'DB_NAME': os.getenv('DB_NAME', 'bot_automation'),
        'DB_SCHEMA': os.getenv('DB_SCHEMA', 'bot'),
        'DB_USER': os.getenv('DB_USER', 'botuser'),
        'DB_PASSWORD': os.getenv('DB_PASSWORD'),
        'EDI_INPUT_DIR': os.getenv('EDI_INPUT_DIR', 'D:\\'),
    }

    if not config['DB_PASSWORD'] or config['DB_PASSWORD'] == 'changeme':
        raise ValueError(
            "DB_PASSWORD is not set. Copy .env.example to .env in the same folder as "
            "edi835-parser.exe and fill in your credentials."
        )

    return config


def get_connection(config: Dict[str, str]) -> Connection:
    """
    Create a PostgreSQL connection with proper schema search path.

    Args:
        config: Configuration dictionary from load_config()

    Returns:
        psycopg2 connection object with autocommit=False

    Raises:
        psycopg2.Error: If connection fails
    """
    conn = psycopg2.connect(
        host=config['DB_HOST'],
        port=config['DB_PORT'],
        database=config['DB_NAME'],
        user=config['DB_USER'],
        password=config['DB_PASSWORD'],
    )

    # Set search path to the bot schema
    with conn.cursor() as cursor:
        cursor.execute(f"SET search_path TO {config['DB_SCHEMA']}")
    conn.commit()

    # Return connection with autocommit disabled for transaction control
    conn.autocommit = False

    return conn
