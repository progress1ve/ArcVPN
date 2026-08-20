import unittest

from database.db_admin_roles import role_allows, role_permissions


class AdminRolesTests(unittest.TestCase):
    def test_owner_can_do_everything(self):
        self.assertTrue(role_allows("owner", "future.permission"))

    def test_support_cannot_create_backups_or_run_node_diagnostics(self):
        self.assertTrue(role_allows("support", "support.reply"))
        self.assertFalse(role_allows("support", "overview.read"))
        self.assertFalse(role_allows("support", "backups.create"))
        self.assertFalse(role_allows("support", "nodes.diagnose"))

    def test_viewer_is_read_only(self):
        permissions = role_permissions("viewer")
        self.assertIn("overview.read", permissions)
        self.assertNotIn("support.reply", permissions)
