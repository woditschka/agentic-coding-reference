"""Classify a representative tree through each stack's skeleton layout.toml, the one the init scaffolds."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import ROOT

# The skeletons are plain data; the runtime that reads them is the core package.
sys.path.insert(0, str(ROOT / "core" / "scripts"))
from grading import config, features

# (path, kind, module, sensitive) per stack. Module ids follow the skeleton's
# strategy: the Gradle module root for Java, the parent directory for Go and
# the generic stack, and a repo-root file's own name. Every sensitive row hits
# exactly one glob, so a glob deleted from a skeleton fails its table.
CASES = {
    "java-spring-boot": [
        ("src/main/java/com/example/Foo.java", "prod", "src", False),
        ("src/test/java/com/example/FooTest.java", "test", "src", False),
        ("src/test/java/com/example/FooTests.java", "test", "src", False),
        ("src/test/java/com/example/FooIT.java", "test", "src", False),
        ("src/main/java/com/example/security/SecurityConfig.java", "prod", "src", True),
        ("src/main/java/com/example/auth/Session.java", "prod", "src", True),
        ("src/test/java/com/example/auth/SessionTest.java", "test", "src", True),
        ("src/main/java/com/example/secretstore/Load.java", "prod", "src", True),
        ("src/main/java/com/example/credentials/Store.java", "prod", "src", True),
        ("src/main/java/com/example/apikeys/Signer.java", "prod", "src", True),
        ("src/main/java/com/example/apitoken/Mint.java", "prod", "src", True),
        ("docs/prd.md", "unknown", None, False),
        ("scripts/grading.py", "unknown", None, False),
    ],
    "go": [
        ("internal/report/summary.go", "prod", "internal/report", False),
        ("internal/report/summary_test.go", "test", "internal/report", False),
        ("cmd/example/main.go", "prod", "cmd/example", False),
        ("pkg/foo/bar.go", "prod", "pkg/foo", False),
        ("main.go", "prod", "main.go", False),
        ("internal/auth/session.go", "prod", "internal/auth", True),
        ("internal/auth/session_test.go", "test", "internal/auth", True),
        ("internal/secretstore/load.go", "prod", "internal/secretstore", True),
        ("internal/credentials/store.go", "prod", "internal/credentials", True),
        ("internal/apikeys/signer.go", "prod", "internal/apikeys", True),
        ("internal/apitoken/mint.go", "prod", "internal/apitoken", True),
        ("docs/prd.md", "unknown", None, False),
        ("scripts/grading.py", "unknown", None, False),
        ("main_test.go", "test", None, False),
    ],
    "generic": [
        ("src/billing/invoice.py", "prod", "src/billing", False),
        ("src/billing/invoice_test.py", "test", "src/billing", False),
        ("src/billing/invoice.spec.ts", "test", "src/billing", False),
        ("src/auth/session.py", "prod", "src/auth", True),
        ("src/secrets/vault.py", "prod", "src/secrets", True),
        ("src/credentials/store.py", "prod", "src/credentials", True),
        ("src/apikeys/signer.py", "prod", "src/apikeys", True),
        ("src/tokens/mint.py", "prod", "src/tokens", True),
        ("docs/prd.md", "unknown", None, False),
        ("tests/test_main.py", "test", None, False),
    ],
}


def _skeleton(stack):
    return config.load_layout(ROOT / "init" / "stacks" / stack / "scripts")


class SkeletonLayouts(unittest.TestCase):
    def test_every_path_classifies_as_the_skeleton_encodes(self):
        for stack, cases in CASES.items():
            layout = _skeleton(stack)
            for path, kind, module, sensitive in cases:
                with self.subTest(stack=stack, path=path, field="kind"):
                    self.assertEqual(features.classify_kind(path, layout), kind)
                with self.subTest(stack=stack, path=path, field="module"):
                    self.assertEqual(features.module_of(path, layout), module)
                with self.subTest(stack=stack, path=path, field="sensitive"):
                    self.assertEqual(features.is_sensitive(path, layout), sensitive)


if __name__ == "__main__":
    unittest.main(verbosity=2)
