from app.llm.groq_client import generate_text


# -----------------------------------
# Paragraph Summary
# -----------------------------------

def summarize_paragraph(paragraph_text: str) -> str:
    """
    Generate a one sentence summary of a paragraph.
    """

    prompt = f"""
You are helping build a structured understanding of a story.

Summarize the following paragraph in ONE concise sentence.

Paragraph:
{paragraph_text}

Return only the summary.
"""

    summary = generate_text(prompt)

    return summary.strip()


# -----------------------------------
# Chapter Summary
# -----------------------------------

def summarize_chapter(paragraph_summaries: list[str]) -> str:
    """
    Generate summary of a chapter from paragraph summaries.
    """

    joined = "\n".join(paragraph_summaries)

    prompt = f"""
Below are summaries of paragraphs from a chapter.

Create a concise summary describing the overall events of the chapter.

Paragraph summaries:
{joined}

Return a short paragraph summary.
"""

    summary = generate_text(prompt)

    return summary.strip()


# -----------------------------------
# Document Summary
# -----------------------------------

def summarize_document(chapter_summaries: list[str]) -> str:
    """
    Generate summary of entire document.
    """

    joined = "\n".join(chapter_summaries)

    prompt = f"""
Below are summaries of chapters from a book.

Create a short summary describing the overall story.

Chapters:
{joined}

Return a concise book summary.
"""

    summary = generate_text(prompt)

    return summary.strip()