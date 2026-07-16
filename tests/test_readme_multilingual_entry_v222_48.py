from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def test_root_readme_links_all_three_user_guides_and_overviews():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    required = (
        "docs/user/ru/index.md",
        "docs/user/kk/index.md",
        "docs/user/en/index.md",
        "README.ru.md",
        "README.kk.md",
        "README.en.md",
    )
    for target in required:
        assert f"]({target})" in text
        assert (ROOT / target).is_file()


def test_language_indexes_are_nonempty_and_link_registered_documents():
    manifest = json.loads((ROOT / "docs/documentation_manifest.json").read_text(encoding="utf-8"))
    for audience in ("user", "developer"):
        for language in ("ru", "kk", "en"):
            index = ROOT / "docs" / audience / language / "index.md"
            text = index.read_text(encoding="utf-8")
            assert len(text.strip()) > 100
            relevant = [d for d in manifest["documents"] if d["audience"] == audience and d["id"] != f"{audience}_documentation_index"]
            for document in relevant:
                target = Path(document["languages"][language])
                assert f"]({target.name})" in text
                assert (ROOT / "docs" / target).is_file()


def test_manifest_registers_language_indexes_at_same_revision():
    manifest = json.loads((ROOT / "docs/documentation_manifest.json").read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in manifest["documents"]}
    for document_id in ("user_documentation_index", "developer_documentation_index"):
        item = by_id[document_id]
        assert item["revision"] == 1
        assert set(item["languages"]) == {"ru", "kk", "en"}
        for path in item["languages"].values():
            assert (ROOT / "docs" / path).is_file()
