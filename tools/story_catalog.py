"""Shared, non-destructive story catalog publishing helpers."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


CATEGORY_NAMES = [
    "Hewan dan Fabel",
    "Petualangan dan Penemuan",
    "Keluarga dan Persahabatan",
    "Alam dan Lingkungan",
    "Sejarah dan Budaya",
    "Kehidupan Sehari-hari",
    "Misteri dan Imajinasi",
    "Nilai dan Pertumbuhan",
]

# Broad themes intentionally span both books.  Story titles and source order
# remain in the source files; this map only controls library categorization.
CATEGORIES = {
    "book1-story-01-the-lion-and-the-rabbit": "Hewan dan Fabel",
    "book1-story-02-the-laboratory": "Keluarga dan Persahabatan",
    "book1-story-03-the-report": "Petualangan dan Penemuan",
    "book1-story-04-the-dogs-bell": "Hewan dan Fabel",
    "book1-story-05-the-jackal-and-the-sun-child": "Hewan dan Fabel",
    "book1-story-06-the-friendly-ghost": "Misteri dan Imajinasi",
    "book1-story-07-the-best-prince": "Sejarah dan Budaya",
    "book1-story-08-how-the-sun-and-the-moon-were-made": "Sejarah dan Budaya",
    "book1-story-09-the-starfish": "Alam dan Lingkungan",
    "book1-story-10-the-first-peacock": "Sejarah dan Budaya",
    "book1-story-11-princess-rose-and-the-creature": "Keluarga dan Persahabatan",
    "book1-story-12-the-crazy-artist": "Misteri dan Imajinasi",
    "book1-story-13-the-farmer-and-the-cats": "Nilai dan Pertumbuhan",
    "book1-story-14-a-magical-book": "Misteri dan Imajinasi",
    "book1-story-15-the-big-race": "Hewan dan Fabel",
    "book1-story-16-adams-countys-gold": "Petualangan dan Penemuan",
    "book1-story-17-the-race-for-water": "Alam dan Lingkungan",
    "book1-story-18-the-little-red-chicken": "Hewan dan Fabel",
    "book1-story-19-shipwrecked": "Petualangan dan Penemuan",
    "book1-story-20-the-seven-cities-of-gold": "Petualangan dan Penemuan",
    "book1-story-21-katy": "Kehidupan Sehari-hari",
    "book1-story-22-a-better-reward": "Hewan dan Fabel",
    "book1-story-23-the-camp": "Keluarga dan Persahabatan",
    "book1-story-24-a-strong-friendship": "Keluarga dan Persahabatan",
    "book1-story-25-joes-pond": "Alam dan Lingkungan",
    "book1-story-26-archie-and-his-donkey": "Hewan dan Fabel",
    "book1-story-27-the-spider-and-the-bird": "Hewan dan Fabel",
    "book1-story-28-the-party": "Keluarga dan Persahabatan",
    "book1-story-29-how-the-world-got-light": "Sejarah dan Budaya",
    "book1-story-30-cats-and-secrets": "Misteri dan Imajinasi",
    "book2-story-01-the-twelve-months": "Alam dan Lingkungan",
    "book2-story-02-the-dragon": "Misteri dan Imajinasi",
    "book2-story-03-the-battle-of-thermopylae": "Sejarah dan Budaya",
    "book2-story-04-the-deer-and-his-image": "Hewan dan Fabel",
    "book2-story-05-may-29-1953": "Petualangan dan Penemuan",
    "book2-story-06-the-frog-prince": "Nilai dan Pertumbuhan",
    "book2-story-07-a-beautiful-bird": "Petualangan dan Penemuan",
    "book2-story-08-tricky-turtle": "Hewan dan Fabel",
    "book2-story-09-the-tale-of-bartelby-oboyle": "Nilai dan Pertumbuhan",
    "book2-story-10-blackbeard": "Sejarah dan Budaya",
    "book2-story-11-dinosaur-drawings": "Misteri dan Imajinasi",
    "book2-story-12-the-mean-chef": "Kehidupan Sehari-hari",
    "book2-story-13-the-cat-and-the-fox": "Hewan dan Fabel",
    "book2-story-14-the-good-student": "Kehidupan Sehari-hari",
    "book2-story-15-the-lucky-knife": "Petualangan dan Penemuan",
    "book2-story-16-prince-sam": "Misteri dan Imajinasi",
    "book2-story-17-henry-fords-famous-car": "Sejarah dan Budaya",
    "book2-story-18-the-priest": "Kehidupan Sehari-hari",
    "book2-story-19-mrs-may-and-the-green-girl": "Keluarga dan Persahabatan",
    "book2-story-20-albert-einstein": "Sejarah dan Budaya",
    "book2-story-21-from-the-earth-to-the-stars": "Petualangan dan Penemuan",
    "book2-story-22-the-farm-festival": "Keluarga dan Persahabatan",
    "book2-story-23-the-clever-thief": "Nilai dan Pertumbuhan",
    "book2-story-24-the-doctors-cure": "Keluarga dan Persahabatan",
    "book2-story-25-the-criminal": "Nilai dan Pertumbuhan",
    "book2-story-26-the-two-captains": "Sejarah dan Budaya",
    "book2-story-27-the-duke-and-the-minister": "Sejarah dan Budaya",
    "book2-story-28-the-fisherman": "Petualangan dan Penemuan",
    "book2-story-29-osiris-and-the-nile": "Alam dan Lingkungan",
    "book2-story-30-the-taxi-driver": "Kehidupan Sehari-hari",
}


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.write_bytes(json_bytes(value))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _reference(root: Path, path: Path) -> dict[str, Any]:
    story = json.loads(path.read_text(encoding="utf-8"))
    relative = path.relative_to(root / "storie").as_posix()
    return {
        "id": story["id"],
        "collectionId": story["collectionId"],
        "family": story["family"],
        "category": story["category"],
        "level": story["level"],
        "order": story["order"],
        "sourceOrder": story["sourceOrder"],
        "path": relative,
        "sha256": sha256_file(path),
        "sentenceCount": story["sentenceCount"],
        "title": story["title"],
        "summary": story["summary"],
        "image": story["image"],
        "assets": story["assets"],
    }


def _validate_references(references: list[dict[str, Any]]) -> None:
    ids: set[str] = set()
    paths: set[str] = set()
    for reference in references:
        story_id = reference.get("id")
        path = reference.get("path")
        if not isinstance(story_id, str) or story_id in ids:
            raise ValueError(f"Duplicate story id in merged catalog: {story_id!r}")
        if not isinstance(path, str) or path in paths:
            raise ValueError(f"Duplicate story filename in merged catalog: {path!r}")
        ids.add(story_id)
        paths.add(path)


def publish_collection(
    root: Path,
    collection: dict[str, Any],
    references: list[dict[str, Any]],
    audit_path: Path,
) -> None:
    """Publish one book while retaining every other indexed/discovered book.

    Existing entries for this collection may be updated, but an existing story
    cannot disappear merely because a generator was run for the other book.
    Orphaned story JSON files are discovered and retained as a final guard
    against the historical index-replacement failure.
    """
    story_root = root / "storie"
    collection_id = collection["id"]
    collection_dir = story_root / collection_id
    on_disk = [
        _reference(root, path)
        for path in sorted(collection_dir.glob("*.json"))
        if path.name not in {"index.json", "source-audit.json"}
    ]
    generated_ids = {item["id"] for item in references}
    disk_ids = {item["id"] for item in on_disk}
    if not disk_ids.issubset(generated_ids):
        missing = sorted(disk_ids - generated_ids)
        raise ValueError(f"Refusing to drop existing story files: {missing}")

    root_index_path = story_root / "index.json"
    existing: dict[str, Any] = {}
    if root_index_path.is_file():
        existing = json.loads(root_index_path.read_text(encoding="utf-8"))

    existing_collections = existing.get("collections", [])
    if not existing_collections and existing.get("id") and existing.get("stories"):
        # Upgrade the pre-merge single-book index without dropping its entries.
        old_id = existing["id"]
        existing_collections = [
            {
                "id": old_id,
                "order": 1,
                "title": existing.get("title", {}),
                "description": existing.get("description", {}),
                "storyCount": len(existing["stories"]),
                "sourceAudit": existing.get("sourceAudit", {}),
            }
        ]
        other_references = list(existing["stories"]) if old_id != collection_id else []
    else:
        other_references = [
            item
            for item in existing.get("stories", [])
            if item.get("collectionId") != collection_id
        ]

    # Recover valid story files that were present on disk but absent from an
    # accidentally replaced index.
    indexed_paths = {item.get("path") for item in other_references}
    for item in on_disk:
        if item["id"] not in generated_ids and item["path"] not in indexed_paths:
            other_references.append(item)

    old_current = [
        item
        for item in existing.get("stories", [])
        if item.get("collectionId") == collection_id
    ]
    old_ids = {item.get("id") for item in old_current}
    if not old_ids.issubset(generated_ids):
        raise ValueError(f"Refusing to drop existing indexed stories: {sorted(old_ids - generated_ids)}")

    current = [dict(item) for item in references]
    all_references = other_references + current
    _validate_references(all_references)

    # Each book keeps a directly auditable index in addition to the aggregate.
    book_index = {
        "schemaVersion": 1,
        "id": collection_id,
        "languagePair": {"reference": "id", "target": "fil"},
        "title": collection["title"],
        "description": collection["description"],
        "storyCount": len(current),
        "sourceAudit": {"path": "source-audit.json", "sha256": sha256_file(audit_path)},
        "stories": sorted(current, key=lambda item: item["order"]),
    }
    book_index_path = collection_dir / "index.json"
    write_json(book_index_path, book_index)

    by_id = {item["id"]: item for item in existing_collections if item.get("id") != collection_id}
    by_id[collection_id] = {
        "id": collection_id,
        "order": collection.get("order", len(by_id) + 1),
        "index": f"{collection_id}/index.json",
        "sha256": sha256_file(book_index_path),
        "title": collection["title"],
        "description": collection["description"],
        "storyCount": len(current),
        "sourceAudit": {
            "path": f"{collection_id}/source-audit.json",
            "sha256": sha256_file(audit_path),
        },
    }
    merged_collections = sorted(by_id.values(), key=lambda item: (item.get("order", 999), item["id"]))
    counts = Counter(item["category"] for item in all_references)
    categories = [
        {"id": f"category-{index:02d}", "name": name, "storyCount": counts.get(name, 0)}
        for index, name in enumerate(CATEGORY_NAMES, 1)
        if counts.get(name, 0)
    ]
    root_audit = {
        "schemaVersion": 1,
        "type": "story-collection-audit",
        "storyCount": len(all_references),
        "bookCount": len(merged_collections),
        "collections": [
            {
                "id": item["id"],
                "storyCount": item["storyCount"],
                "index": item["index"],
                "sourceAudit": item["sourceAudit"],
            }
            for item in merged_collections
        ],
        "categories": categories,
    }
    root_audit_path = story_root / "source-audit.json"
    write_json(root_audit_path, root_audit)
    aggregate = {
        "schemaVersion": 1,
        "id": "4000-essential-english-words",
        "languagePair": {"reference": "id", "target": "fil"},
        "title": {
            "id": "Cerita dari 4000 Essential English Words — Buku 1 dan 2",
            "fil": "Mga Kuwento mula sa 4000 Essential English Words — Book 1 at 2",
        },
        "description": {
            "id": "Enam puluh retelling ringkas dalam bahasa Tagalog dengan terjemahan Indonesia dari Buku 1 dan Buku 2.",
            "fil": "Animnapung maiikling muling pagsasalaysay sa Tagalog na may salin sa Indonesian mula sa Book 1 at Book 2.",
        },
        "storyCount": len(all_references),
        "bookCount": len(merged_collections),
        "sourceAudit": {"path": "source-audit.json", "sha256": sha256_file(root_audit_path)},
        "categories": categories,
        "collections": merged_collections,
        "stories": sorted(
            all_references,
            key=lambda item: (
                next(c["order"] for c in merged_collections if c["id"] == item["collectionId"]),
                item["order"],
            ),
        ),
    }
    write_json(root_index_path, aggregate)

    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["stories"] = {
        "index": "storie/index.json",
        "sha256": sha256_file(root_index_path),
    }
    write_json(manifest_path, manifest)


def category_for(story_id: str, fallback: str) -> str:
    return CATEGORIES.get(story_id, fallback)
