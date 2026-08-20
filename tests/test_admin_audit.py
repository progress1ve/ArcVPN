import sqlite3
import unittest

from database.migrations import migration_49


class AdminAuditMigrationTests(unittest.TestCase):
    def test_events_are_append_only(self):
        conn = sqlite3.connect(":memory:")
        try:
            migration_49(conn)
            conn.execute("INSERT INTO admin_audit_events(actor_type,action,outcome) VALUES('admin','login','success')")
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("UPDATE admin_audit_events SET outcome='changed'")
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("DELETE FROM admin_audit_events")
        finally:
            conn.close()
