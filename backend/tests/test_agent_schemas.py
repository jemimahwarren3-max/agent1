import pytest
from pydantic import ValidationError

from app.agents.schemas import (
    DiscoveredBusiness,
    DiscoveryResult,
    GeneratedEmail,
    LeadScoreResult,
    ResearchExtraction,
    SourcedField,
)


def test_lead_score_result_valid():
    result = LeadScoreResult(score=72.5, classification="warm", explanation="Decent fit.")
    assert result.score == 72.5


def test_lead_score_result_rejects_out_of_range_score():
    with pytest.raises(ValidationError):
        LeadScoreResult(score=150, classification="hot", explanation="x")


def test_research_extraction_requires_source_for_each_field():
    extraction = ResearchExtraction(
        business_description="A hotel in Harare.",
        business_emails=[SourcedField(value="info@example.com", source_url="https://example.com/contact")],
    )
    assert extraction.business_emails[0].source_url == "https://example.com/contact"


def test_research_extraction_defaults_are_empty_not_fabricated():
    extraction = ResearchExtraction()
    assert extraction.business_emails == []
    assert extraction.business_description == ""


def test_discovery_result_roundtrip():
    result = DiscoveryResult(
        businesses=[
            DiscoveredBusiness(
                business_name="Example Hotel",
                website="https://example-hotel.co.zw",
                discovery_source="https://google.com/search?q=hotels+harare",
            )
        ],
        search_queries_used=["hotels in Harare"],
    )
    assert len(result.businesses) == 1


def test_generated_email_schema():
    email = GeneratedEmail(
        subject="An opportunity for Example Hotel",
        body="Hello...",
        template_category="website_development",
    )
    assert email.template_category == "website_development"
