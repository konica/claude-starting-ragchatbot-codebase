# Plan: Deduplicate and Sort Source Citations

## Problem

ChromaDB returns up to `MAX_RESULTS` (5) chunks per search. Multiple chunks can originate from the same lesson, which produces duplicate source entries (e.g. "Lesson 6" appearing 3× when 3 of the 5 returned chunks are from Lesson 6). The order also reflects ChromaDB's similarity ranking, not lesson order.

**Observed**: Lesson 6 × 3, Lesson 1 × 1, Lesson 3 × 1 → should be: Lesson 1, Lesson 3, Lesson 6

## Root Cause

In `CourseSearchTool._format_results()` (`backend/search_tools.py`), every chunk result appends its own `{"label", "url"}` entry to `sources` with no deduplication or sorting.

## Fix

All changes are confined to `_format_results()` in `backend/search_tools.py`. No other files need changing.

### Approach

1. **Deduplicate** — track seen `(course_title, lesson_num)` pairs with a `set`. Skip appending a source if that pair has already been recorded.
2. **Sort** — after building the deduplicated list, sort by `(course_title, lesson_num)` so sources appear in lesson-number ascending order (alphabetically by course first, then by lesson number).

### Code

```python
def _format_results(self, results: SearchResults) -> str:
    formatted = []
    sources = []
    seen = set()  # track (course_title, lesson_num) pairs

    for doc, meta in zip(results.documents, results.metadata):
        course_title = meta.get('course_title', 'unknown')
        lesson_num = meta.get('lesson_number')

        # Build context header (unchanged)
        header = f"[{course_title}"
        if lesson_num is not None:
            header += f" - Lesson {lesson_num}"
        header += "]"
        formatted.append(f"{header}\n{doc}")

        # Deduplicate sources
        key = (course_title, lesson_num)
        if key in seen:
            continue
        seen.add(key)

        label = course_title
        if lesson_num is not None:
            label += f" - Lesson {lesson_num}"
        url = (
            self.store.get_lesson_link(course_title, lesson_num)
            if lesson_num is not None
            else self.store.get_course_link(course_title)
        )
        sources.append({"label": label, "url": url, "_sort_key": (course_title, lesson_num or 0)})

    # Sort ascending by course title then lesson number
    sources.sort(key=lambda s: s["_sort_key"])
    # Remove internal sort key before storing
    for s in sources:
        del s["_sort_key"]

    self.last_sources = sources
    return "\n\n".join(formatted)
```

## Files to Modify

| File | Change |
|---|---|
| `backend/search_tools.py` | `_format_results()` — add `seen` set for deduplication; sort `sources` before storing |

## Verification

1. Start server: `./run.sh`
2. Query: "List out advanced retrieval techniques"
3. Expand Sources — should show: Lesson 1, Lesson 3, Lesson 6 (each once, ascending order)
