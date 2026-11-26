"""Publishing invariants, including safe reruns and distinct word forms."""

import json
import tempfile
import unittest
from pathlib import Path

from global_vocabulary import key, migrate, read, validate, write


class VocabularyPublishingTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "storie").mkdir()
        write(self.root / "storie/index.json", {"stories": []})
        write(self.root / "manifest.json", {"stories": {"index": "storie/index.json", "sha256": ""}})

    def tearDown(self):
        self.temporary.cleanup()

    def story(self, identifier, words):
        data = {"id": identifier, "sentences": [{"fil": " ".join(words), "id": "Contoh"}],
                "vocabulary": [{"word": word, "language": "fil", "translations": {"id": "arti " + word},
                                "meanings": {"id": "makna " + word}, "notes": {"id": "catatan"},
                                "pos": "noun", "pronunciation": word} for word in words]}
        write(self.root / "storie" / (identifier + ".json"), data)
        return data

    def test_normalization_does_not_merge_different_words(self):
        self.assertEqual(key("  Bahay  ’to "), "bahay 'to")
        self.assertNotEqual(key("bata"), key("batà"))
        self.assertNotEqual(key("araw-araw"), key("araw araw"))
        self.assertNotEqual(key("lakad"), key("lumakad"))

    def test_lossless_merging_contexts_and_idempotency(self):
        first = self.story("first", ["Usa", "batà", "bata"])
        second = self.story("second", ["usa", "bahay"])
        migrate(self.root)
        entries = validate(self.root)
        self.assertEqual(4, len(entries))
        deer = entries["usa"]
        self.assertEqual({"first", "second"}, set(deer["storyRefs"]))
        self.assertEqual(2, len(deer["sources"]))
        self.assertEqual(first["vocabulary"][0], deer["sources"][0]["data"])
        self.assertEqual(2, len(deer["examples"]))
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*.json")}
        migrate(self.root)
        after = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*.json")}
        self.assertEqual(before, after)

    def test_new_file_preserves_existing_ids_and_shard_assignments(self):
        self.story("first", [f"word{i}" for i in range(100)])
        migrate(self.root)
        first = read(self.root / "vocabulary/index.json")
        self.story("next", ["new-word", "word0"])
        migrate(self.root)
        current = read(self.root / "vocabulary/index.json")
        self.assertEqual(2, len(current["files"]))
        self.assertEqual(101, current["entryCount"])
        self.assertEqual(first["entries"], current["entries"][:100])
        validate(self.root)

    def test_duplicate_ids_words_and_hash_corruption_are_rejected(self):
        self.story("first", ["usa", "bahay"])
        migrate(self.root)
        path = self.root / "vocabulary/vocabulary-001.json"
        original = path.read_bytes()
        index = read(self.root / "vocabulary/index.json")
        for field in ("id", "word"):
            document = json.loads(original)
            document["entries"][1][field] = document["entries"][0][field]
            index["files"][0]["sha256"] = write(path, document)
            write(self.root / "vocabulary/index.json", index)
            with self.assertRaises(ValueError):
                migrate(self.root)
        path.write_bytes(b"{}")
        with self.assertRaises(ValueError):
            migrate(self.root)


if __name__ == "__main__":
    unittest.main()
