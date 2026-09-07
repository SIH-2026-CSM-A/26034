"""Regression checks for the reviews module's dependency and claim boundaries."""

import ast
from pathlib import Path

from app.core import ConsumerSafetyClaim
from app.modules.reviews.schemas import PublishedReviewsResponse, ReviewSubmissionResponse

REVIEWS_SOURCE_ROOT = Path(__file__).parents[3] / "app" / "modules" / "reviews"


def python_sources() -> list[Path]:
    """Return every Python source file owned by the reviews package."""
    return sorted(REVIEWS_SOURCE_ROOT.glob("*.py"))


def test_reviews_imports_only_core_contracts_and_itself() -> None:
    """Keep the detachable module independent from every other feature package."""
    imported_modules: set[str] = set()
    for source_path in python_sources():
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_modules.add(node.module)

    feature_imports = {
        module
        for module in imported_modules
        if module.startswith("app.modules.") and not module.startswith("app.modules.reviews")
    }

    assert feature_imports == set()


def test_reviews_does_not_import_ai_or_similarity_packages() -> None:
    """Keep publication as deterministic counting without an inference dependency."""
    forbidden_roots = {
        "agent",
        "anthropic",
        "embeddings",
        "langchain",
        "llm",
        "openai",
        "sentence_transformers",
        "transformers",
    }
    imported_roots: set[str] = set()
    for source_path in python_sources():
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_roots.add(node.module.split(".", 1)[0])

    assert imported_roots.isdisjoint(forbidden_roots)


def test_public_shapes_keep_consumer_sentiment_as_the_claim() -> None:
    """Keep public response fields in consumer-sentiment vocabulary only."""
    assert set(ReviewSubmissionResponse.model_fields) == {
        "product_identifier",
        "consumer_safety_claim",
        "publication_status",
    }
    assert (
        ReviewSubmissionResponse.model_fields["consumer_safety_claim"].annotation
        is ConsumerSafetyClaim
    )
    assert set(PublishedReviewsResponse.model_fields) == {
        "product_identifier",
        "published_consensus",
    }


def test_public_shapes_do_not_expose_compliance_output_fields() -> None:
    """Keep consumer sentiment responses separate from compliance output names."""
    public_field_names = set(ReviewSubmissionResponse.model_fields) | set(
        PublishedReviewsResponse.model_fields
    )
    prohibited_output_names = {
        "compliance_status",
        "verdict",
        "potential_violation",
        "rule_finding",
        "violation",
        "non_compliance",
        "enforcement_decision",
    }

    assert public_field_names.isdisjoint(prohibited_output_names)
