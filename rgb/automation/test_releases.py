import unittest

from releases import rgb_tag, select, version


def release(tag, **kwargs):
    return dict(tag_name=tag, draft=False, prerelease=False, **kwargs)


class ReleaseSelectionTest(unittest.TestCase):
    def test_only_supported_stable_missing_releases(self):
        releases = [release("1.4.3"), release("1.5.1"), release("1.6.0"),
                    release("nightly"), dict(tag_name="1.7.0", draft=False, prerelease=True),
                    dict(tag_name="1.8.0", draft=True, prerelease=False)]
        self.assertEqual(select(releases, {rgb_tag("1.5.1")}), ["1.6.0"])

    def test_catches_up_in_version_order(self):
        self.assertEqual(select([release("1.10.0"), release("1.9.0")], set()),
                         ["1.9.0", "1.10.0"])

    def test_hook_cannot_build_arbitrary_ref(self):
        for tag in ["dev", "../main", "1.5.1\nanything", "$(id)", "1.5.1-rc"]:
            with self.assertRaises(ValueError):
                version(tag)
        with self.assertRaises(ValueError):
            select([release("1.5.1")], set(), "9.9.9")

    def test_hook_is_idempotent(self):
        self.assertEqual(select([release("1.5.1")], {rgb_tag("1.5.1")}, "1.5.1"), [])


if __name__ == "__main__":
    unittest.main()
