import sqlite3

DB_NAME = "mcp.db"


def init_db():

    conn = sqlite3.connect(DB_NAME)

    c = conn.cursor()

    # =========================================
    # PROCESSED FILES TABLE
    # =========================================

    c.execute("""

    CREATE TABLE IF NOT EXISTS processed_files (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        file_path TEXT UNIQUE,

        status TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )

    """)

    # =========================================
    # SOURCE CONFIG TABLE
    # =========================================

    c.execute("""

    CREATE TABLE IF NOT EXISTS source_configs (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        control_name TEXT NOT NULL,

        dp_name TEXT NOT NULL,

        organization_name TEXT NOT NULL,

        source_type TEXT NOT NULL,

        source_name TEXT,

        is_active INTEGER DEFAULT 1,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )

    """)

    # =========================================
    # SOURCE CREDENTIALS TABLE
    # =========================================

    c.execute("""

    CREATE TABLE IF NOT EXISTS source_credentials (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        source_config_id INTEGER NOT NULL,

        config_json TEXT NOT NULL,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(source_config_id)
        REFERENCES source_configs(id)
    )

    """)

    conn.commit()
    conn.close()