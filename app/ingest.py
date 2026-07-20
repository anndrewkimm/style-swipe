"""Command-line ingestion of garment images from a local folder."""

import argparse
from pathlib import Path

from sqlmodel import Session, select

from app import db
from app.models import Item

IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp"})
VALID_SOURCES = frozenset({"seed", "candidate"})


def ingest_folder(folder: Path, source: str) -> int:
    """Create items for new image paths directly inside a folder."""
    if source not in VALID_SOURCES:
        raise ValueError("source must be 'seed' or 'candidate'")
    if not folder.is_dir():
        raise ValueError(f"not a directory: {folder}")

    db.init_db()
    with Session(db.engine) as session:
        existing_paths = set(session.exec(select(Item.image_path)).all())
        image_paths = sorted(
            path
            for path in folder.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        )

        added = 0
        for image_path in image_paths:
            stored_path = str(image_path)
            if stored_path in existing_paths:
                continue

            session.add(Item(source=source, image_path=stored_path))
            existing_paths.add(stored_path)
            added += 1

        session.commit()
    return added


def main() -> None:
    """Parse CLI arguments and ingest the requested folder."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--source", choices=sorted(VALID_SOURCES), required=True)
    args = parser.parse_args()

    count = ingest_folder(args.folder, args.source)
    print(f"Ingested {count} item(s).")


if __name__ == "__main__":
    main()
