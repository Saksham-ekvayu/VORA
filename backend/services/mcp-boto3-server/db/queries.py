# db/queries.py

import sqlite3
import json
from db.models import DB_NAME


# =========================================
# PROCESSED FILES
# =========================================

def is_processed(file_path):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM processed_files WHERE file_path=?",
        (file_path,)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None


def mark_processed(file_path, status="done"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO processed_files (file_path, status)
            VALUES (?, ?)
        """, (file_path, status))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"mark_processed error: {e}")
    finally:
        conn.close()


# =========================================
# SOURCE CONFIG / CREDENTIALS
# =========================================

def save_source_config(data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO source_configs (
                control_name, dp_name, organization_name,
                source_type, source_name
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            data.control_name,
            data.dp_name,
            data.organization_name,
            data.source_type,
            data.source_name
        ))

        source_config_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO source_credentials (source_config_id, config_json)
            VALUES (?, ?)
        """, (source_config_id, json.dumps(data.config_json)))

        conn.commit()
        return source_config_id

    except Exception as e:
        conn.rollback()
        print(f"save_source_config error: {e}")
        return None

    finally:
        conn.close()


# =========================================
# SECTIONS / CONTROLS / DEPLOYMENT POINTS
# =========================================

def save_sections_config(data):
    """
    data: SectionsConfigRequest
    Upserts sections -> controls -> deployment_points.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        for section in data.sections:
            cursor.execute("""
                INSERT INTO sections (id, name)
                VALUES (?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name
            """, (section.id, section.name))

            for control in section.controls:
                cursor.execute("""
                    INSERT INTO controls (id, section_id, name, description)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        section_id = excluded.section_id,
                        name = excluded.name,
                        description = excluded.description
                """, (control.id, section.id, control.name, control.description))

                for dp in control.deployment_points:
                    cursor.execute("""
                        INSERT INTO deployment_points (
                            id, control_id, name, status, path, weightage, remark
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            control_id = excluded.control_id,
                            name = excluded.name,
                            status = excluded.status,
                            path = excluded.path,
                            weightage = excluded.weightage,
                            remark = excluded.remark
                    """, (
                        dp.id, control.id, dp.name, dp.status,
                        dp.path, dp.weightage, dp.remark
                    ))

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        print(f"save_sections_config error: {e}")
        return False

    finally:
        conn.close()


def save_full_config(data):
    """
    data: FullConfigRequest
    Saves source config first, then sections config.
    Returns a dict with both results so the caller can see partial failures.
    """
    source_config_id = save_source_config(data.source_config)
    sections_success = save_sections_config(data.sections_config)

    return {
        "source_config_id": source_config_id,
        "sections_success": sections_success
    }


def get_sections_config():
    """
    Rebuilds nested {sections: [{controls: [{deployment_points: [...]}]}]}.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        sections_rows = cursor.execute("SELECT * FROM sections").fetchall()
        controls_rows = cursor.execute("SELECT * FROM controls").fetchall()
        dp_rows = cursor.execute("SELECT * FROM deployment_points").fetchall()

        dps_by_control = {}
        for dp in dp_rows:
            dps_by_control.setdefault(dp["control_id"], []).append({
                "id": dp["id"],
                "name": dp["name"],
                "status": dp["status"],
                "path": dp["path"],
                "weightage": dp["weightage"],
                "remark": dp["remark"],
            })

        controls_by_section = {}
        for ctrl in controls_rows:
            controls_by_section.setdefault(ctrl["section_id"], []).append({
                "id": ctrl["id"],
                "name": ctrl["name"],
                "description": ctrl["description"],
                "deployment_points": dps_by_control.get(ctrl["id"], []),
            })

        sections = []
        for sec in sections_rows:
            sections.append({
                "id": sec["id"],
                "name": sec["name"],
                "controls": controls_by_section.get(sec["id"], []),
            })

        return sections

    except Exception as e:
        print(f"get_sections_config error: {e}")
        return None

    finally:
        conn.close()