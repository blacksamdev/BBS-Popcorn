import os
import sqlite3
import time


# Whitelist stricte des schémas connus — aucune valeur externe n'entre dans les requêtes
KNOWN_SCHEMAS = [
    ("moz_cookies", "host", "name", "value", "path", "expiry",  "isSecure"),
    ("Cookie",      "host", "name", "value", "path", "expires", "secure"),
    ("cookies",     "host", "name", "value", "path", "expires", "secure"),
]

# Colonnes autorisées — whitelist complète
ALLOWED_COLUMNS = {
    "host", "name", "value", "path",
    "expiry", "expires", "isSecure", "secure"
}

# Tables autorisées
ALLOWED_TABLES = {"moz_cookies", "Cookie", "cookies"}


class CookieExporter:
    NETSCAPE_HEADER = "# Netscape HTTP Cookie File\n"

    def __init__(self, sqlite_path: str, output_path: str):
        self.sqlite_path = sqlite_path
        self.output_path = output_path

    def _check_identifier(self, name: str, allowed: set) -> str:
        """Vérifie qu'un identifiant est dans la whitelist — lève une exception sinon."""
        if name not in allowed:
            raise ValueError(f"Identifiant non autorisé : {name}")
        return name

    def detect_schema(self, cur):
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
        print(f"[cookies] Tables trouvées : {tables}")

        for schema in KNOWN_SCHEMAS:
            if schema[0] in tables:
                print(f"[cookies] Schéma détecté : {schema[0]}")
                return schema

        # Schéma inconnu — tente de deviner depuis les tables connues uniquement
        for table in tables & ALLOWED_TABLES:
            cur.execute("PRAGMA table_info(?)", (table,))
            cols = {row[1] for row in cur.fetchall()}
            if {"host", "name", "value", "path"}.issubset(cols):
                expires = "expiry"   if "expiry"   in cols & ALLOWED_COLUMNS else \
                          "expires"  if "expires"  in cols & ALLOWED_COLUMNS else None
                secure  = "isSecure" if "isSecure" in cols & ALLOWED_COLUMNS else \
                          "secure"   if "secure"   in cols & ALLOWED_COLUMNS else None
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

            # Vérifie chaque identifiant contre la whitelist
            t  = self._check_identifier(table,    ALLOWED_TABLES)
            ch = self._check_identifier(c_host,   ALLOWED_COLUMNS)
            cn = self._check_identifier(c_name,   ALLOWED_COLUMNS)
            cv = self._check_identifier(c_value,  ALLOWED_COLUMNS)
            cp = self._check_identifier(c_path,   ALLOWED_COLUMNS)
            ce = self._check_identifier(c_expires,ALLOWED_COLUMNS)
            cs = self._check_identifier(c_secure, ALLOWED_COLUMNS)

            # Construction sécurisée — tous les identifiants sont whitelistés
            query = (
                f"SELECT {ch}, "
                f"CASE WHEN {ch} LIKE '.%' THEN 'TRUE' ELSE 'FALSE' END, "
                f"{cp}, "
                f"CASE WHEN {cs} = 1 THEN 'TRUE' ELSE 'FALSE' END, "
                f"{ce}, {cn}, {cv} FROM {t}"
            )
            cur.execute(query)
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
