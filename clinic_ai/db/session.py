import os
import psycopg2
from contextlib import contextmanager
from psycopg2.extras import RealDictCursor


def _get_db_url() -> str:
    """Read DB URL at runtime so it works regardless of import order."""
    url = os.getenv("SUPABASE_DB_URL", "")
    if not url or "your-password" in url or "your-project" in url:
        return ""          # placeholder → treat as unconfigured
    return url


@contextmanager
def db_session(clinic_id=None):
    db_url = _get_db_url()
    if not db_url:
        raise RuntimeError("SUPABASE_DB_URL is not set or contains placeholder values")
    conn = psycopg2.connect(db_url)
    try:
        if clinic_id:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL app.current_clinic_id = %s", (str(clinic_id),))
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

@contextmanager
def db_cursor(clinic_id=None):
    with db_session(clinic_id=clinic_id) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
