import os
import sqlite3
import time


class CookieExporter:
    NETSCAPE_HEADER = "# Netscape HTTP Cookie File\n"

    KNOWN_SCHEMAS = [
        ("moz_cookies", "host", "name", "value", "path", "expiry",  "isSecure"),
        ("Cookie",      "host", "name", "value", "path", "expires", "secure"),
        ("cookies",     "host", "name", "value", "path", "expires", "secure"),
    ]

    def __init__(self, sqlite_path: str, output_path: str):
        self.sqlite_path = sqlite_path
        self.output_path = output_path

    def detect_schema(self, cur):
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
        print(f"[cookies] Tables trouvées : {tables}")

        for schema in self.KNOWN_SCHEMAS:
            if schema[0] in tables:
                print(f"[cookies] Schéma détecté : {schema[0]}")
                return schema

        for table in tables:
            cur.execute(f"PRAGMA table_info({table})")
            cols = {row[1] for row in cur.fetchall()}
            if {"host", "name", "value", "path"}.issubset(cols):
                expires = "expiry"   if "expiry"   in cols else \
                          "expires"  if "expires"  in cols else None
                secure  = "isSecure" if "isSecure" in cols else \
                          "secure"   if "secure"   in cols else None
                if expires and secure:
                    print(f"[cookies] Schéma inconnu adapté : {table}")
                    return (table, "host", "name", "value", "path", expires, secure)

        return None

    def export(self) -> bool:
        if not os.path.exists(self.sqlite_path):
            print("[cookies] SQLite introuvable, pas encore de session.")
            return False
        try:
            con = sqlite3.connect(self.sqlite_path)
            cur = con.cursor()

            schema = self.detect_schema(cur)
            if not schema:
                print("[cookies] Schéma de cookies non reconnu.")
                con.close()
                return False

            table, c_host, c_name, c_value, c_path, c_expires, c_secure = schema

            cur.execute(f"""
                SELECT
                    {c_host},
                    CASE WHEN {c_host} LIKE '.%' THEN 'TRUE' ELSE 'FALSE' END,
                    {c_path},
                    CASE WHEN {c_secure} = 1 THEN 'TRUE' ELSE 'FALSE' END,
                    {c_expires},
                    {c_name},
                    {c_value}
                FROM {table}
            """)
            rows = cur.fetchall()
            con.close()

            with open(self.output_path, "w") as f:
                f.write(self.NETSCAPE_HEADER)
                for row in rows:
                    host, include_sub, path, secure, expires, name, value = row
                    if expires is None or expires == 0:
                        expires = int(time.time()) + 86400 * 365
                    f.write(
                        f"{host}\t{include_sub}\t{path}\t"
                        f"{secure}\t{expires}\t{name}\t{value}\n"
                    )
            print(f"[cookies] {len(rows)} cookies exportés → {self.output_path}")
            return True

        except Exception as e:
            print(f"[cookies] Erreur export : {e}")
            return False
