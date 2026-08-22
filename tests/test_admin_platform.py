import sqlite3
import unittest

from database.migrations import migration_52, migration_53


class AdminPlatformTests(unittest.TestCase):
    def test_migration_creates_catalog_and_expenses(self):
        connection = sqlite3.connect(":memory:")
        migration_52(connection)
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        self.assertIn("subscription_profile_overrides", tables)
        self.assertIn("service_expenses", tables)
        migration_53(connection)
        columns = {row[1] for row in connection.execute(
            "PRAGMA table_info(subscription_profile_overrides)"
        )}
        self.assertIn("include_in_auto", columns)

if __name__ == "__main__":
    unittest.main()
