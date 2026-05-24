"""Section-aware text chunking for resume and JD embedding."""
from __future__ import annotations

import re
from typing import Dict, List

TARGET_CHUNK_TOKENS = 200
MIN_CHUNK_TOKENS = 20
TOKEN_MULTIPLIER = 1.3

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _estimate_tokens(text: str) -> float:
    return len(text.split()) * TOKEN_MULTIPLIER


def _split_sentences(text: str) -> List[str]:
    if not text or not text.strip():
        return []
    normalized = text.replace(".\n", ". ")
    parts = _SENTENCE_SPLIT.split(normalized)
    return [part.strip() for part in parts if part.strip()]


def chunk_text(text: str, section_label: str = "general") -> List[Dict]:
    """
    Split text into sentence-based chunks targeting ~200 estimated tokens.

    Chunks shorter than 20 estimated tokens are discarded.
    """
    sentences = _split_sentences(text)
    if not sentences:
        return []

    chunks: List[Dict] = []
    current_sentences: List[str] = []
    current_tokens = 0.0
    chunk_idx = 0

    def _emit() -> None:
        nonlocal chunk_idx, current_sentences, current_tokens
        if not current_sentences:
            return
        chunk_body = " ".join(current_sentences)
        if _estimate_tokens(chunk_body) >= MIN_CHUNK_TOKENS:
            chunks.append(
                {
                    "text": chunk_body,
                    "section": section_label,
                    "chunk_idx": chunk_idx,
                }
            )
            chunk_idx += 1
        current_sentences = []
        current_tokens = 0.0

    for sentence in sentences:
        sentence_tokens = _estimate_tokens(sentence)
        if current_sentences and current_tokens + sentence_tokens > TARGET_CHUNK_TOKENS:
            _emit()
        current_sentences.append(sentence)
        current_tokens += sentence_tokens
        if current_tokens >= TARGET_CHUNK_TOKENS:
            _emit()

    _emit()
    return chunks


def chunk_resume(sections: List[Dict]) -> List[Dict]:
    """
    Chunk each resume section and return a single list with continuous chunk_idx.
    """
    merged: List[Dict] = []
    next_idx = 0
    for section in sections:
        label = section.get("section", "general")
        text = section.get("text", "")
        section_chunks = chunk_text(text, section_label=label)
        for chunk in section_chunks:
            chunk["chunk_idx"] = next_idx
            next_idx += 1
            merged.append(chunk)
    return merged
