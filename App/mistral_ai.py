"""Compatibility shim.

Historically this project stored Groq-backed LLM helpers in this file.
The implementation now lives in `App.groq_ai`.
"""

from .groq_ai import (  # noqa: F401
    GROQ_API_URL,
    GROQ_MODEL,
    api_key,
    client,
    analyze_prediction_with_llm,
    generate_care_instructions,
    generate_tree_explanation,
)