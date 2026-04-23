import os
import sqlite3
import time


KNOWN_SCHEMAS = [
    ("moz_cookies", "host", "name", "value", "path", "expiry", "isSecure"),
    ("Cookie", "host", "name", "value", "path", "expires", "secure"),
    ("cookies", "host", "name", "value", "path", "expires", "secure"),
]

ALLOWED_COLUMNS = {
    "host", "name", "value", "path",
    "expiry", "expires", "isSecure", "secure"
}

ALLOWED_TABLES = {"moz_cookies", "Cookie", "cookies"}


class CookieExporter:

    NETSCAPE_HEADER = "# Netscape HTTP Cookie File\n"

    def __init__(self, sqlite_path: str, output_path: str):
        self.sqlite_path = sqlite_path
        self.output_path = output_path

    def _check(self, name: str, allowed: set) -> str:
        if not name or name not in allowed:
            raise ValueError("invalid identifier")
        return name

    def detect_schema(self, cur):
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {r[0] for r in cur.fetchall()}

        for schema in KNOWN_SCHEMAS:
            if schema[0] in tables:
                return schema

        for table in tables & ALLOWED_TABLES:
            cur.execute(f"PRAGMA table_info({table})")
            cols = {r[1] for r in cur.fetchall()}

            if {"host", "name", "value", "path"}.issubset(cols):
                expires = "expiry" if "expiry" in cols else "expires"
                secure = "isSecure" if "isSecure" in cols else "secure"
                return (table, "host", "name", "value", "path", expires, secure)

        return None

    def export(self) -> bool:
        if not os.path.exists(self.sqlite_path):
            return False

        try:
            con = sqlite3.connect(self.sqlite_path)
            cur = con.cursor()

            schema = self.detect_schema(cur)
            if not schema:
                return False

            table, host, name, value, path, expires, secure = schema

            table = self._check(table, ALLOWED_TABLES)

            query = f"""
                SELECT
                    {host},
                    CASE WHEN {host} LIKE '.%' THEN 'TRUE' ELSE 'FALSE' END,
                    {path},
                    CASE WHEN {secure} = 1 THEN 'TRUE' ELSE 'FALSE' END,
                    {expires},
                    {name},
                    {value}
                FROM {table}
            """

            cur.execute(query)
            rows = cur.fetchall()
            con.close()

            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

            with open(self.output_path, "w") as f:
                f.write(self.NETSCAPE_HEADER)

                for host, sub, path, secure, exp, name, val in rows:
                    if not exp:
                        exp = int(time.time()) + 31536000

                    f.write(f"{host}\t{sub}\t{path}\t{secure}\t{exp}\t{name}\t{val}\n")

            return True

        except Exception:
            return False
