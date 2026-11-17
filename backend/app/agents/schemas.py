"""Structured output contracts for every agent. Passed as `output_schema` on the
ADK LlmAgent so Gemini is constrained to return valid JSON matching these shapes
— this is the "Structured JSON outputs with validation" requirement from the brief.
"""

from pydantic import BaseModel, Field


class DiscoveredBusiness(BaseModel):
    business_name: str
    website: str = Field(description="Official website URL, not a directory/listing page")
    location_hint: str = Field(default="", description="City/country if mentioned in the result")
    discovery_source: str = Field(description="The search result URL this business was found via")


class DiscoveryResult(BaseModel):
    businesses: list[DiscoveredBusiness]
    search_queries_used: list[str]


class SourcedField(BaseModel):
    """A single extracted fact plus exactly where it came from — required so the
    research agent never reports a contact detail it can't point to on the page."""

    value: str
    source_url: str


class ResearchExtraction(BaseModel):
    business_description: str = Field(default="")
    services_offered: list[str] = Field(default_factory=list)
    business_emails: list[SourcedField] = Field(default_factory=list)
    phone_numbers: list[SourcedField] = Field(default_factory=list)
    contact_person: SourcedField | None = None
    social_links: list[str] = Field(default_factory=list)
    observed_technology: list[str] = Field(
        default_factory=list, description="CMS/booking/POS systems etc. observed on the site"
    )
    identified_opportunity: str = Field(
        default="", description="A concrete, specific gap Haki Systems could plausibly help with"
    )
    recommended_service: str = Field(default="")
    crawled_urls: list[str] = Field(default_factory=list)
    could_not_extract_reason: str = Field(
        default="", description="Set if the site couldn't be crawled or had no useful content"
    )


class LeadScoreResult(BaseModel):
    score: float = Field(ge=0, le=100)
    classification: str = Field(description="one of: hot, warm, cold, unqualified")
    explanation: str


class GeneratedEmail(BaseModel):
    subject: str
    body: str
    template_category: str = Field(
        description="one of: general_introduction, website_development, ai_automation, "
        "ai_customer_support, workflow_automation, custom_software, industry_specific, follow_up"
    )


class ReplyClassificationResult(BaseModel):
    classification: str = Field(
        description="one of: interested, requesting_info, wants_meeting, not_interested, "
        "out_of_office, unsubscribe, other"
    )
    summary: str = Field(description="One sentence summarizing what the reply actually said")
