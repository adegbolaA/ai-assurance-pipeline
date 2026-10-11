"""Keyword retriever over the policy corpus.

Deliberately simple — no embedding model — so the only model in the supply
chain is the registered, hosted one.
"""

import re
from dataclasses import dataclass
from pathlib import Path

CORPUS_DIR = Path(__file__).parents[1] / "corpus"
_word = re.compile(r"[a-z0-9]+")
_stop = set("the a an and or of to in is for on what how are do does i my be it".split())


@dataclass
class Passage:
    source: str
    text: str


def _terms(text: str) -> set[str]:
    return {w for w in _word.findall(text.lower()) if w not in _stop}


def load_corpus(corpus_dir: Path = CORPUS_DIR) -> list[Passage]:
    passages = []
    for doc in sorted(corpus_dir.glob("*.md")):
        for block in doc.read_text(encoding="utf-8").split("\n\n"):
            if block.strip() and not block.startswith("#"):
                passages.append(Passage(doc.name, block.strip()))
    return passages


def retrieve(question: str, passages: list[Passage], k: int = 2) -> list[Passage]:
    q = _terms(question)
    scored = [(len(q & _terms(p.text)), p) for p in passages]
    scored = [s for s in scored if s[0] > 0]
    scored.sort(key=lambda s: s[0], reverse=True)
    return [p for _, p in scored[:k]]
