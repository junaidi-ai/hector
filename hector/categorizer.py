from typing import Iterable, List


def categorize_repository(name: str, description: str, categories: Iterable[str]) -> List[str]:
    """Assign categories by simple keyword matching in name/description."""
    text = f"{name} {description}".lower()
    matched: List[str] = []
    for cat in categories:
        norm = str(cat).strip()
        if not norm:
            continue
        if norm.lower() in text:
            matched.append(norm)
    return matched
