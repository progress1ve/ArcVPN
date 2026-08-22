import sqlite3
import unittest

from database.migrations import migration_52


class AdminPlatformTests(unittest.TestCase):
    def test_migration_creates_catalog_and_expenses(self):
        connection = sqlite3.connect(":memory:")
        migration_52(connection)
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        self.assertIn("subscription_profile_overrides", tables)
        self.assertIn("service_expenses", tables)

if __name__ == "__main__":
    unittest.main()
