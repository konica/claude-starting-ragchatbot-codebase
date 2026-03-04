---
paths:
  - "backend/*.py"
---

# API Rules

## Request Validation

All API request models must validate input before the endpoint handler runs.

Use Pydantic v2 `field_validator` on every request model in `backend/app.py`:

- **String fields**: strip whitespace; reject blank/empty values
- **Length limits**: enforce a sensible max (e.g. `query` ≤ 2000 chars)
- **Optional string fields**: strip whitespace; coerce whitespace-only to `None`

Example for `QueryRequest`:

```python
from pydantic import BaseModel, field_validator

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query must not be empty or whitespace")
        if len(v) > 2000:
            raise ValueError("query must not exceed 2000 characters")
        return v

    @field_validator("session_id")
    @classmethod
    def session_id_strip(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip() or None
        return v
```

FastAPI automatically returns **HTTP 422 Unprocessable Entity** with field-level error details when any validator fails — no extra error handling needed in the endpoint.
