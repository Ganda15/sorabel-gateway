import re
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DELIVERABLE_ROOT = REPOSITORY_ROOT / "docs" / "livrable"
BRIEF_ROOT = REPOSITORY_ROOT / "docs" / "brief"
PRESENTATION_ROOT = DELIVERABLE_ROOT / "presentation"


def test_trainer_deliverable_has_one_clear_entry_point() -> None:
    assert (DELIVERABLE_ROOT / "README.md").is_file()
    assert (DELIVERABLE_ROOT / "architecture" / "RAG-AVANCE-ARCHITECTURE.md").is_file()
    assert (PRESENTATION_ROOT / "index.html").is_file()
    assert (PRESENTATION_ROOT / "START-PRESENTATION.bat").is_file()
    assert all(
        (BRIEF_ROOT / filename).is_file()
        for filename in (
            "01-rag-avance.md",
            "02-text-to-sql.md",
            "03-mcp-matrice-acces.md",
        )
    )


def test_presentation_uses_current_paths_and_has_no_personal_absolute_path() -> None:
    presentation_sources = [
        PRESENTATION_ROOT / "app.js",
        PRESENTATION_ROOT / "index.html",
        PRESENTATION_ROOT / "styles.css",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in presentation_sources)

    assert "C:/Users/kanda" not in combined
    assert "data-note" not in combined
    assert "Note orale" not in combined
    assert combined.count('<section class="slide') == 10


def test_private_preparation_is_not_inside_public_repository() -> None:
    assert not (REPOSITORY_ROOT / "docs" / "study").exists()
    assert not (REPOSITORY_ROOT / "docs" / "oral").exists()
    assert not (REPOSITORY_ROOT / "docs" / "superpowers").exists()
    assert not (REPOSITORY_ROOT / "docs" / "development").exists()


def test_every_presentation_source_link_resolves_inside_repository() -> None:
    html = (PRESENTATION_ROOT / "index.html").read_text(encoding="utf-8")
    relative_paths = {
        value
        for value in re.findall(r'(?:src|href)="([^"]+)"', html)
        if "://" not in value and not value.startswith("#")
    }

    assert relative_paths == {"app.js", "styles.css"}
    missing = sorted(path for path in relative_paths if not (PRESENTATION_ROOT / path).is_file())
    assert missing == []


def test_navigation_markdown_links_resolve() -> None:
    navigation_files = [
        REPOSITORY_ROOT / "README.md",
        BRIEF_ROOT / "README.md",
        DELIVERABLE_ROOT / "README.md",
        DELIVERABLE_ROOT / "conception" / "README.md",
        PRESENTATION_ROOT / "README.md",
    ]
    missing: list[str] = []

    for document in navigation_files:
        content = document.read_text(encoding="utf-8")
        for raw_target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", content):
            target = raw_target.split("#", maxsplit=1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (document.parent / target).resolve()
            if not resolved.exists():
                missing.append(f"{document.relative_to(REPOSITORY_ROOT)} -> {target}")

    assert missing == []
