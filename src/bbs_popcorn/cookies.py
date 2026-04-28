import os
import sqlite3
import shutil
import tempfile
import time


KNOWN_SCHEMAS = [
    ("moz_cookies", "host", "name", "value", "path", "expiry", "isSecure"),
    ("Cookie", "host", "name", "value", "path", "expires", "secure"),
    ("cookies", "host", "name", "value", "path", "expires", "secure"),
]

ALLOWED_TABLES = {"moz_cookies", "Cookie", "cookies"}

EXPORT_QUERIES = {
    "moz_cookies": """
        SELECT
            host,
            CASE WHEN host LIKE '.%' THEN 'TRUE' ELSE 'FALSE' END,
            path,
            CASE WHEN isSecure = 1 THEN 'TRUE' ELSE 'FALSE' END,
            expiry,
            name,
            value
        FROM moz_cookies
    """,
    "Cookie": """
        SELECT
            host,
            CASE WHEN host LIKE '.%' THEN 'TRUE' ELSE 'FALSE' END,
            path,
            CASE WHEN secure = 1 THEN 'TRUE' ELSE 'FALSE' END,
            expires,
            name,
            value
        FROM Cookie
    """,
    "cookies": """
        SELECT
            host,
            CASE WHEN host LIKE '.%' THEN 'TRUE' ELSE 'FALSE' END,
            path,
            CASE WHEN secure = 1 THEN 'TRUE' ELSE 'FALSE' END,
            expires,
            name,
            value
        FROM cookies
    """,
}


class CookieExporter:

    NETSCAPE_HEADER = "# Netscape HTTP Cookie File\n"

    def __init__(self, sqlite_path: str, output_path: str):
        self.sqlite_path = sqlite_path
        self.output_path = output_path

    def _is_allowed_cookie_host(self, host: str) -> bool:
        if not host:
            return False
        normalized = host.lstrip(".").lower()
        allowed_domains = (
            "youtube.com",
            "youtu.be",
            "google.com",
            "googlevideo.com",
            "ytimg.com",
        )
        return any(
            normalized == domain or normalized.endswith(f".{domain}")
            for domain in allowed_domains
        )

    def detect_schema(self, cur):
        for schema in KNOWN_SCHEMAS:
            table = schema[0]
            cur.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
                (table,)
            )
            if cur.fetchone():
                return schema

        return None

    def export(self) -> bool:
        if not os.path.exists(self.sqlite_path):
            return False

        tmp_db = None
        tmp_output = None
        try:
            # WebKit may keep the live DB busy; read from a temp copy.
            with tempfile.NamedTemporaryFile(prefix="bbs-popcorn-cookies-", suffix=".sqlite", delete=False) as tmp_file:
                tmp_db = tmp_file.name
            shutil.copy2(self.sqlite_path, tmp_db)

            con = sqlite3.connect(tmp_db)
            cur = con.cursor()

            schema = self.detect_schema(cur)
            if not schema:
                con.close()
                return False

            table, *_ = schema
            if table not in ALLOWED_TABLES:
                con.close()
                return False
            query = EXPORT_QUERIES.get(table)
            if not query:
                con.close()
                return False

            cur.execute(query)
            rows = cur.fetchall()
            con.close()

            output_dir = os.path.dirname(self.output_path)
            os.makedirs(output_dir, mode=0o700, exist_ok=True)

            fd, tmp_output = tempfile.mkstemp(
                prefix="cookies-",
                suffix=".txt",
                dir=output_dir
            )
            os.close(fd)
            os.chmod(tmp_output, 0o600)

            with open(tmp_output, "w", encoding="utf-8") as f:
                f.write(self.NETSCAPE_HEADER)

                for host, sub, path, secure, exp, name, val in rows:
                    if not self._is_allowed_cookie_host(host):
                        continue
                    if not exp:
                        exp = int(time.time()) + 31536000
                    f.write(f"{host}\t{sub}\t{path}\t{secure}\t{exp}\t{name}\t{val}\n")

            os.replace(tmp_output, self.output_path)
            os.chmod(self.output_path, 0o600)

            return True

        except Exception:
            return False
        finally:
            if tmp_db and os.path.exists(tmp_db):
                try:
                    os.remove(tmp_db)
                except OSError:
                    pass
            if tmp_output and os.path.exists(tmp_output):
                try:
                    os.remove(tmp_output)
                except OSError:
                    pass
