"""The workspace's member table, read from a real layout file."""

import tempfile
import unittest
from pathlib import Path

from changeset.workspace import Member, WorkspaceError, load_members, unreached_globs

SOME_STACK = "java-spring-boot"
CONTRACT_GLOBS = ("src/main/proto/**",)


def a_member(**fields):
    values = {
        "key": "api",
        "path": "../product-api",
        "stack": SOME_STACK,
        "contracts": (),
        "depends_on": (),
    }
    values.update(fields)
    return Member(**values)


def members_from_text(text):
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "layout.toml").write_text(text, encoding="utf-8")
        return load_members(Path(tmp))


def entry(key, path, stack=SOME_STACK, extra=""):
    return f'{key} = {{ path = "{path}", stack = "{stack}"{extra} }}\n'


class MemberTable(unittest.TestCase):
    def test_a_layout_without_a_workspace_table_is_a_single_repository(self):
        self.assertEqual(members_from_text("test = []\n"), ())

    def test_a_workspace_table_without_members_is_a_single_repository(self):
        self.assertEqual(members_from_text("[workspace]\n"), ())

    def test_one_member_is_read_with_its_declared_fields(self):
        text = "[workspace.members]\n" + entry(
            "api", "../product-api", extra=', contracts = ["src/main/proto/**"]'
        )
        self.assertEqual(members_from_text(text), (a_member(contracts=CONTRACT_GLOBS),))

    def test_members_keep_their_declared_order(self):
        text = (
            "[workspace.members]\n"
            + entry("web", "../product-web", extra=', depends_on = ["api"]')
            + entry("api", "../product-api")
        )
        self.assertEqual([m.key for m in members_from_text(text)], ["web", "api"])

    def test_a_dependency_names_a_declared_member(self):
        text = (
            "[workspace.members]\n"
            + entry("api", "../product-api")
            + entry("web", "../product-web", extra=', depends_on = ["api"]')
        )
        self.assertEqual(members_from_text(text)[1].depends_on, ("api",))

    def test_a_missing_layout_is_a_broken_install(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(WorkspaceError):
            load_members(Path(tmp))

    def test_an_unparsable_layout_is_a_broken_install(self):
        with self.assertRaises(WorkspaceError):
            members_from_text("[workspace.members\n")


class MemberValidation(unittest.TestCase):
    def assert_rejected(self, body):
        with self.assertRaises(WorkspaceError):
            members_from_text("[workspace.members]\n" + body)

    def test_a_workspace_that_is_not_a_table_is_rejected(self):
        with self.assertRaises(WorkspaceError):
            members_from_text("workspace = 1\n")

    def test_a_key_with_an_uppercase_letter_is_rejected(self):
        self.assert_rejected(entry("Api", "../product-api"))

    def test_an_entry_that_is_not_a_table_is_rejected(self):
        self.assert_rejected('api = "../product-api"\n')

    def test_an_absolute_path_is_rejected(self):
        self.assert_rejected(entry("api", "/srv/product-api"))

    def test_a_path_inside_the_umbrella_is_rejected(self):
        self.assert_rejected(entry("api", "members/product-api"))

    def test_the_parent_directory_itself_is_rejected(self):
        self.assert_rejected(entry("api", ".."))

    def test_a_path_that_climbs_back_after_leaving_is_rejected(self):
        self.assert_rejected(entry("api", "../product-api/../other"))

    def test_a_path_with_a_control_byte_is_rejected_before_git_sees_it(self):
        self.assert_rejected(entry("api", "../product\\u0000api"))

    def test_a_missing_stack_is_allowed_and_reads_as_none(self):
        members = members_from_text(
            '[workspace.members]\napi = { path = "../product-api" }\n'
        )
        self.assertIsNone(members[0].stack)

    def test_a_stack_that_is_not_a_name_is_rejected(self):
        self.assert_rejected(entry("api", "../product-api", stack="Java 25"))

    def test_a_trailing_slash_is_rejected(self):
        self.assert_rejected(entry("api", "../product-api/"))

    def test_a_tab_in_the_path_is_rejected(self):
        self.assert_rejected(entry("api", "../product\tapi"))

    def test_the_umbrella_itself_under_another_spelling_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            umbrella = Path(tmp) / "product"
            (umbrella / "scripts").mkdir(parents=True)
            (umbrella / "scripts" / "layout.toml").write_text(
                "[workspace.members]\n" + entry("me", "../product"), encoding="utf-8"
            )
            with self.assertRaises(WorkspaceError):
                load_members(umbrella / "scripts")

    def test_contracts_that_are_not_a_list_is_rejected(self):
        self.assert_rejected(
            entry("api", "../product-api", extra=', contracts = "src/**"')
        )

    def test_an_empty_contract_glob_is_rejected(self):
        self.assert_rejected(entry("api", "../product-api", extra=', contracts = [""]'))

    def test_a_dependency_on_an_undeclared_member_is_rejected(self):
        self.assert_rejected(
            entry("web", "../product-web", extra=', depends_on = ["api"]')
        )

    def test_a_dependency_on_itself_is_rejected(self):
        self.assert_rejected(
            entry("api", "../product-api", extra=', depends_on = ["api"]')
        )


class UnreachedGlobs(unittest.TestCase):
    def test_a_project_glob_reaches_no_member_and_is_not_dead(self):
        self.assertEqual(unreached_globs(("vendor/**",), (a_member(),)), ())

    def test_a_glob_under_a_members_path_is_reached(self):
        self.assertEqual(unreached_globs(("../product-api/gen/**",), (a_member(),)), ())

    def test_a_wildcard_segment_reaches_every_matching_member(self):
        self.assertEqual(unreached_globs(("../product-*/gen/**",), (a_member(),)), ())

    def test_a_glob_under_no_declared_member_is_dead(self):
        self.assertEqual(
            unreached_globs(("../other/gen/**",), (a_member(),)), ("../other/gen/**",)
        )


class MemberPresence(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.umbrella = Path(tmp.name) / "product"
        self.umbrella.mkdir()
        self.member = a_member()

    def test_a_member_with_a_git_directory_is_present(self):
        (self.member.root(self.umbrella) / ".git").mkdir(parents=True)
        self.assertTrue(self.member.is_present(self.umbrella))

    def test_a_worktree_link_counts_as_present(self):
        self.member.root(self.umbrella).mkdir(parents=True)
        (self.member.root(self.umbrella) / ".git").write_text("gitdir: elsewhere\n")
        self.assertTrue(self.member.is_present(self.umbrella))

    def test_a_directory_without_a_repository_is_absent(self):
        self.member.root(self.umbrella).mkdir(parents=True)
        self.assertFalse(self.member.is_present(self.umbrella))

    def test_a_missing_directory_is_absent(self):
        self.assertFalse(self.member.is_present(self.umbrella))


if __name__ == "__main__":
    unittest.main()
