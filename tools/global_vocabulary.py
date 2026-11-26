"""Lossless, append-only vocabulary migration/publisher. Run on the data branch.

Existing IDs and shard assignments never change. New words fill the last shard,
then append shards. Normalization preserves accents, hyphens and inflections.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path


def key(word):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", word).strip().lower().replace("’", "'"))


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    temporary = path.with_suffix(".json.part")
    temporary.write_bytes(data)
    temporary.replace(path)
    return hashlib.sha256(data).hexdigest()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add_unique(items, item):
    if item not in items:
        items.append(item)


def migrate(root, corpus=None):
    folder = root / "vocabulary"
    entries, shards, ids = {}, {}, set()
    old = read(folder / "index.json") if (folder / "index.json").exists() else {}
    for shard in old.get("files", []):
        path = shard["path"]
        if not re.fullmatch(r"vocabulary-\d{3,}\.json", path):
            raise ValueError("Unsafe vocabulary path")
        if digest(folder / path) != shard["sha256"]:
            raise ValueError(f"Vocabulary hash mismatch: {path}")
        shards[path] = read(folder / path)["entries"]
        for entry in shards[path]:
            normalized = key(entry["word"])
            if entry["id"] in ids or normalized in entries:
                raise ValueError(f"Duplicate global vocabulary: {entry['id']}")
            entries[normalized] = entry
            ids.add(entry["id"])

    records = 0

    def merge(legacy, stories):
        nonlocal records
        records += 1
        normalized = key(legacy["word"])
        if normalized not in entries:
            slug = re.sub(r"[^\w'-]+", "-", normalized, flags=re.UNICODE).strip("-")
            identifier = slug or "word"
            if identifier in ids:
                identifier += "-" + hashlib.sha256(normalized.encode()).hexdigest()[:12]
            if identifier in ids:
                raise ValueError("Vocabulary ID collision")
            ids.add(identifier)
            entry = dict(id=identifier, word=normalized, language="fil", meanings=[],
                         partOfSpeech=legacy.get("pos", ""), partsOfSpeech=[], pronunciation=legacy.get("pronunciation", normalized),
                         pronunciations=[], examples=[], storyRefs=[], sources=[])
            entries[normalized] = entry
            if not shards or len(next(reversed(shards.values()))) >= 100:
                number = max([int(p[11:-5]) for p in shards] or [0]) + 1
                shards[f"vocabulary-{number:03d}.json"] = []
            next(reversed(shards.values())).append(entry)
        entry = entries[normalized]
        for field, source in (("partsOfSpeech", "pos"), ("pronunciations", "pronunciation")):
            if legacy.get(source):
                add_unique(entry[field], legacy[source])
        for value in (legacy.get("translations", {}).get("id"), legacy.get("meanings", {}).get("id")):
            if value:
                add_unique(entry["meanings"], {"language": "id", "value": value})
        # Retain every original field, including localized notes and senses.
        add_unique(entry["sources"], {"storyRefs": [s["id"] for s in stories], "data": legacy})
        for story in stories:
            add_unique(entry["storyRefs"], story["id"])
            for sentence in story["sentences"]:
                text = sentence.get("fil", sentence.get("tl", ""))
                if re.search(r"(?<![\w’'-])" + re.escape(normalized) + r"(?![\w’'-])", key(text)):
                    add_unique(entry["examples"], {"tagalog": text, "indonesian": sentence["id"], "storyId": story["id"]})
        return entry["id"]

    story_paths = []
    for path in sorted((root / "storie").rglob("*.json")):
        story = read(path)
        if "sentences" not in story:
            continue
        story_paths.append((path, story))
        references = list(story.get("vocabularyIds", []))
        for legacy in story.pop("vocabulary", []):
            add_unique(references, merge(legacy, [story]))
        if any(identifier not in ids for identifier in references):
            raise ValueError(f"Unresolved vocabulary in {path}")
        story["vocabularyIds"] = references
        write(path, story)

    bundled_count = 0
    bundled_stories = []
    if corpus and corpus.exists():
        bundled = read(corpus)
        bundled_stories = bundled["stories"]
        bundled_count = len(bundled["stories"])
        for legacy in bundled["lexicon"]:
            if legacy["language"] not in ("fil", "tl"):
                continue
            normalized = key(legacy["word"])
            contexts = [s for s in bundled["stories"] if any(
                re.search(r"(?<![\w’'-])" + re.escape(normalized) + r"(?![\w’'-])", key(t.get("fil", t.get("tl", ""))))
                for t in s["sentences"]) or normalized in [key(w) for w in s.get("focus", {}).get("fil", [])]]
            merge(legacy, contexts)
        # Store references centrally; Android's bundled lexicon remains a legacy
        # first-install offline fallback and is never a second source of updates.
        bundled_refs = {s["id"]: [e["id"] for e in entries.values() if s["id"] in e["storyRefs"]] for s in bundled["stories"]}
    else:
        bundled_refs = old.get("bundledStoryRefs", {})

    # A known word can occur outside a story's former curated focus list.
    # Connect those occurrences too, without conflating similar spellings.
    for entry in entries.values():
        pattern = re.compile(r"(?<![\w’'-])" + re.escape(key(entry["word"])) + r"(?![\w’'-])")
        for story in [s for _, s in story_paths] + bundled_stories:
            for sentence in story["sentences"]:
                text = sentence.get("fil", sentence.get("tl", ""))
                if pattern.search(key(text)):
                    add_unique(entry["storyRefs"], story["id"])
                    add_unique(entry["examples"], {"tagalog": text, "indonesian": sentence["id"], "storyId": story["id"]})
                    if "vocabularyIds" in story:
                        add_unique(story["vocabularyIds"], entry["id"])
        for story_id in bundled_refs:
            if story_id in entry["storyRefs"]:
                add_unique(bundled_refs[story_id], entry["id"])
    for path, story in story_paths:
        write(path, story)

    files, directory = [], []
    for path, words in shards.items():
        sha = write(folder / path, {"schemaVersion": 1, "entries": words})
        files.append({"path": path, "sha256": sha, "count": len(words)})
        directory.extend({"id": e["id"], "word": e["word"], "meanings": [m["value"] for m in e["meanings"]], "file": path} for e in words)
    report = old.get("migration", {"embeddedRecords": records, "uniqueEntries": len(entries), "duplicatesMerged": records - len(entries), "serverStories": len(story_paths), "bundledStories": bundled_count})
    index = {"schemaVersion": 1, "languagePair": {"reference": "id", "target": "fil"},
             "entryCount": len(entries), "files": files, "entries": directory,
             "bundledStoryRefs": bundled_refs, "migration": report}
    index_hash = write(folder / "index.json", index)
    refresh_story_hashes(root)
    manifest = read(root / "manifest.json")
    manifest["vocabulary"] = {"index": "vocabulary/index.json", "sha256": index_hash}
    manifest["stories"]["sha256"] = digest(root / manifest["stories"]["index"])
    write(root / "manifest.json", manifest)
    return {**report, "files": len(files), "unresolvedReferences": 0}


def refresh_story_hashes(root):
    """Refresh leaves, source audits, per-book indexes, aggregate audit/index."""
    story_root = root / "storie"
    hashes = {p.relative_to(story_root).as_posix(): digest(p) for p in story_root.rglob("*.json") if "sentences" in read(p)}
    for path in sorted(story_root.rglob("source-audit.json"), key=lambda p: -len(p.parts)):
        audit = read(path)
        for story in audit.get("stories", []):
            if story.get("generatedStory") in hashes:
                story["generatedSha256"] = hashes[story["generatedStory"]]
        for collection in audit.get("collections", []):
            ref = collection["sourceAudit"]
            ref["sha256"] = digest(story_root / ref["path"])
        write(path, audit)
    for path in sorted(story_root.rglob("index.json"), key=lambda p: -len(p.parts)):
        index = read(path)
        for story in index.get("stories", []):
            story["sha256"] = hashes[story["path"]]
        if index.get("sourceAudit"):
            ref = index["sourceAudit"]
            ref["sha256"] = digest(path.parent / ref["path"])
        for collection in index.get("collections", []):
            collection["sha256"] = digest(story_root / collection["index"])
            ref = collection["sourceAudit"]
            ref["sha256"] = digest(story_root / ref["path"])
        write(path, index)


def validate(root):
    folder = root / "vocabulary"
    index = read(folder / "index.json")
    entries, words, directory = {}, set(), {}
    for shard in index["files"]:
        if not re.fullmatch(r"vocabulary-\d{3,}\.json", shard["path"]):
            raise ValueError("Unsafe vocabulary path")
        path = folder / shard["path"]
        assert digest(path) == shard["sha256"], path
        rows = read(path)["entries"]
        assert len(rows) == shard["count"] and 0 < len(rows) <= 100
        for entry in rows:
            assert entry["id"] not in entries and key(entry["word"]) not in words, entry["id"]
            assert entry["language"] == "fil" and entry["meanings"] and entry["partOfSpeech"]
            assert all(m["language"] == "id" and m["value"] for m in entry["meanings"])
            assert all(e["tagalog"] and e["indonesian"] and e["storyId"] in entry["storyRefs"] for e in entry["examples"])
            entries[entry["id"]] = entry
            words.add(key(entry["word"]))
            directory[entry["id"]] = {"id": entry["id"], "word": entry["word"], "meanings": [m["value"] for m in entry["meanings"]], "file": shard["path"]}
    assert len(entries) == index["entryCount"] == len(index["entries"])
    assert directory == {e["id"]: e for e in index["entries"]}
    story_ids = set(index.get("bundledStoryRefs", {}))
    for path in (root / "storie").rglob("*.json"):
        story = read(path)
        if "sentences" not in story:
            continue
        story_ids.add(story["id"])
        assert "vocabulary" not in story
        refs = story["vocabularyIds"]
        assert refs and len(refs) == len(set(refs))
        assert all(identifier in entries and story["id"] in entries[identifier]["storyRefs"] for identifier in refs), path
    for story, refs in index.get("bundledStoryRefs", {}).items():
        assert all(identifier in entries and story in entries[identifier]["storyRefs"] for identifier in refs)
    for entry in entries.values():
        assert set(entry["storyRefs"]) <= story_ids
    assert digest(folder / "index.json") == read(root / "manifest.json")["vocabulary"]["sha256"]
    return entries


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if not args.validate_only:
        print(json.dumps(migrate(args.root, args.corpus), indent=2))
    print(f"Validated {len(validate(args.root))} unique global entries")
