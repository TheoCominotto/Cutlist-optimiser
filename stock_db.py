from pathlib import Path
import sqlite3


DATABASE_PATH = Path(__file__).parent / "data" / "stock.db"


_SCHEMA = """
CREATE TABLE IF NOT EXISTS stock (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    length REAL NOT NULL CHECK (length > 0),
    width REAL NOT NULL CHECK (width > 0),
    thickness REAL NOT NULL CHECK (thickness > 0),
    price REAL NOT NULL CHECK (price >= 0),
    link TEXT
)
"""


def _connect():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute(_SCHEMA)
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(stock)")
    }
    if "link" not in columns:
        connection.execute("ALTER TABLE stock ADD COLUMN link TEXT")
        connection.commit()
    return connection


def get_stock():
    """Return stock rows ordered for display in the application."""
    with _connect() as connection:
        return connection.execute(
            """
            SELECT id, name, length, width, thickness, price, link
            FROM stock
            ORDER BY name, length, width, thickness
            """
        ).fetchall()


def add_stock(name, length, width, thickness, price, link=""):
    """Add one stock product to the local catalogue."""
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO stock (name, length, width, thickness, price, link)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, length, width, thickness, price, link or None),
        )


def update_stock(stock_id, name, length, width, thickness, price, link=""):
    """Update one stock product in the local catalogue."""
    with _connect() as connection:
        connection.execute(
            """
            UPDATE stock
            SET name = ?, length = ?, width = ?, thickness = ?, price = ?, link = ?
            WHERE id = ?
            """,
            (name, length, width, thickness, price, link or None, stock_id),
        )
