import unittest

from prepare import published_releases


def release(tag, draft=False, prerelease=False):
    return dict(tag_name=tag, draft=draft, prerelease=prerelease)


class ReleasePickerDataTests(unittest.TestCase):
    def test_numeric_versions_and_patch_revisions_newest_first(self):
        data = [release(tag) for tag in ["rgb-1.9.0-r1", "rgb-1.10.0-r2", "rgb-1.10.0-r10"]]
        self.assertEqual([r["tag_name"] for r in published_releases(data)],
                         ["rgb-1.10.0-r10", "rgb-1.10.0-r2", "rgb-1.9.0-r1"])

    def test_only_published_rgb_stable_releases(self):
        data = [release("rgb-1.5.1-r1"), release("rgb-1.6.0-r1", draft=True),
                release("rgb-1.7.0-r1", prerelease=True), release("1.8.0"),
                release("rgb-1.9.0-rc-r1")]
        self.assertEqual([r["tag_name"] for r in published_releases(data)], ["rgb-1.5.1-r1"])

    def test_local_single_release_input(self):
        data = release("rgb-1.5.1-r1")
        self.assertEqual(published_releases(data), [data])


if __name__ == "__main__":
    unittest.main()
