import math
from typing import List, Dict, Set, Optional
from app.models import CargoSystem, Item, Position


def calculate_idf(term: str, documents: Dict[str, List[str]], total_docs: int) -> float:
    containing_docs = sum(1 for doc_terms in documents.values() if term in doc_terms)
    return math.log((total_docs + 1) / (containing_docs + 1)) + 1


def calculate_bm25_score(query_terms: List[str], documents: Dict[str, List[str]], k1=1.5, b=0.75) -> Dict[str, float]:
    total_length = sum(len(doc) for doc in documents.values())
    avg_doc_length = total_length / max(1, len(documents))

    # Calculate document frequencies
    total_docs = len(documents)

    # Calculate IDF for each query term
    idf_values = {term: calculate_idf(term, documents, total_docs) for term in query_terms}

    # Calculate BM25 scores
    scores = {}
    for doc_id, doc_terms in documents.items():
        score = 0
        doc_length = len(doc_terms)

        for term in query_terms:
            if term not in doc_terms:
                continue

            # Count term frequency in document
            tf = doc_terms.count(term)

            # BM25 formula
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_length / avg_doc_length)

            score += idf_values[term] * (numerator / denominator)

        scores[doc_id] = score

    return scores


def spatial_filter(items: List[Item], location: Position, radius: float) -> List[Item]:
    """Filter items by spatial proximity"""
    if not location or radius <= 0:
        return items

    filtered_items = []

    for item in items:
        if not item.position:
            continue

        # Calculate Euclidean distance
        distance = location.distance_to(item.position)

        if distance <= radius:
            filtered_items.append(item)

    return filtered_items


def search_items(query: str, cargo_system: CargoSystem, location: Optional[Position] = None,
                 radius: Optional[float] = None, priority: Optional[int] = None) -> List[Item]:
    """BM25 + Spatial Filtering for item search"""
    if not query and not location and priority is None:
        return list(cargo_system.items.values())

    # Extract query terms
    query_terms = query.lower().split() if query else []

    # Filter by priority first if specified
    items_to_search = cargo_system.items.values()
    if priority is not None:
        items_to_search = [item for item in items_to_search if item.priority == priority]

    # If only spatial search, skip BM25
    if not query_terms and location and radius:
        return spatial_filter(list(items_to_search), location, radius)

    # Create documents from items
    documents = {}
    for item in items_to_search:
        # Extract searchable terms from item
        terms = []
        terms.extend(item.name.lower().split())
        terms.extend(item.id.lower().split())
        terms.extend(item.preferred_zone.lower().split())

        documents[item.id] = terms

    # If no valid query terms, return all items
    if not query_terms:
        return list(items_to_search)

    # Calculate BM25 scores
    scores = calculate_bm25_score(query_terms, documents)

    # Filter out items with zero score
    result_items = [
        cargo_system.items[item_id]
        for item_id, score in scores.items()
        if score > 0 and item_id in cargo_system.items
    ]

    # Sort by score (descending)
    result_items.sort(key=lambda item: scores[item.id], reverse=True)

    # Apply spatial filtering if location is provided
    if location and radius:
        result_items = spatial_filter(result_items, location, radius)

    return result_items
