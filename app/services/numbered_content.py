from typing import Dict, List, Optional

from app.services.graph_service import get_document_chapters, get_node


def get_numbered_lines(paragraph_text: str) -> List[Dict]:
    lines = paragraph_text.split("\n")
    return [
        {"line_number": index, "text": line}
        for index, line in enumerate(lines, 1)
    ]


def get_numbered_chapter(document_id: str, chapter_number: int) -> Optional[Dict]:
    chapters = get_document_chapters(document_id)
    if chapter_number < 1 or chapter_number > len(chapters):
        return None

    chapter = chapters[chapter_number - 1]
    raw_paragraphs = chapter.get("children_ids") or []
    paragraphs: List[Dict] = []

    for paragraph_number, paragraph_id in enumerate(raw_paragraphs, 1):
        paragraph = get_node(paragraph_id)
        if not paragraph or paragraph.get("type") != "paragraph":
            continue
        text = paragraph.get("text") or ""
        paragraphs.append(
            {
                "paragraph_number": paragraph_number,
                "paragraph_id": paragraph["id"],
                "text": text,
                "lines": get_numbered_lines(text),
            }
        )

    return {
        "chapter_number": chapter_number,
        "chapter_id": chapter["id"],
        "title": chapter.get("title") or f"Chapter {chapter_number}",
        "summary": chapter.get("summary") or "",
        "content": "\n\n".join(p["text"] for p in paragraphs),
        "paragraphs": paragraphs,
    }


def build_numbered_document_view(
    document_id: str,
    chapter_numbers: Optional[List[int]] = None,
) -> List[Dict]:
    chapters = get_document_chapters(document_id)
    selected = set(chapter_numbers or [])
    results: List[Dict] = []

    for index, _chapter in enumerate(chapters, 1):
        if selected and index not in selected:
            continue
        numbered = get_numbered_chapter(document_id, index)
        if numbered:
            results.append(numbered)
    return results


def get_chapter_number_by_id(document_id: str, chapter_id: str) -> Optional[int]:
    chapters = get_document_chapters(document_id)
    for index, chapter in enumerate(chapters, 1):
        if chapter["id"] == chapter_id:
            return index
    return None
