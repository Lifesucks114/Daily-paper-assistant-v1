from typing import Any


def is_xos_production_scope(paper: dict[str, Any]) -> bool:
    text = f"{paper.get('title', '')} {paper.get('abstract', '')} {paper.get('reason_for_relevance', '')}".lower()
    required_terms = [
        "xos",
        "xylooligosaccharide",
        "xylooligosaccharides",
        "xylan",
        "xylanase",
        "hemicellulose",
        "arabinoxylan",
    ]
    hard_exclusions = [
        "hydrogel",
        "sensor",
        "teng",
        "biomedical",
        "hernia",
        "wound",
        "anticoagulant",
        "antiplatelet",
        "uranium",
        "battery",
        "energy storage",
        "wastewater",
        "cancer",
        "tumor",
    ]
    return any(term in text for term in required_terms) and not any(term in text for term in hard_exclusions)


def simple_relevance_score(paper: dict[str, Any], matched_keywords: list[str]) -> float:
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    score = min(5.0, len(set(matched_keywords)) * 0.5)

    substrate_terms = [
        "xylooligosaccharide",
        "xylooligosaccharides",
        "xos",
        "xylan",
        "xylanase",
        "hemicellulose",
        "arabinoxylan",
        "oligosaccharide",
    ]
    production_terms = [
        "acid hydrolysis",
        "enzymatic hydrolysis",
        "hydrolysis",
        "autohydrolysis",
        "pretreatment",
        "extraction",
        "fractionation",
        "saccharification",
        "sugar release",
        "purification",
        "hplc",
        "membrane",
    ]
    substrate_hits = sum(1 for term in substrate_terms if term in text)
    production_hits = sum(1 for term in production_terms if term in text)

    for term in substrate_terms:
        if term in text:
            score += 0.6
    for term in production_terms:
        if term in text:
            score += 0.35

    if substrate_hits and production_hits:
        score += 1.0
    elif not substrate_hits:
        score = min(score, 1.2)

    return round(min(5.0, score), 1)
