from sqlalchemy import Column, Integer, String, Boolean, Float, Text, ForeignKey, JSON, DateTime, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

# ==========================================
# SYSTEM / CONFIG
# ==========================================
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class IndustryConfig(Base):
    __tablename__ = "industry_configs"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    signals = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DevaciaOffer(Base):
    __tablename__ = "devacia_offers"
    id = Column(Integer, primary_key=True, index=True)
    industry_id = Column(Integer, ForeignKey("industry_configs.id"))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ProviderHealth(Base):
    """Last known state of an external enrichment provider.

    API credentials intentionally do not live in this table.  Render remains
    the source of truth for secrets; this model only gives the UI a durable,
    actionable explanation when a provider is rate-limited or out of credits.
    """
    __tablename__ = "provider_health"
    id = Column(Integer, primary_key=True, index=True)
    provider_name = Column(String(100), nullable=False, unique=True, index=True)
    state = Column(String(50), nullable=False, default="unknown")
    message = Column(Text)
    last_http_status = Column(Integer)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# ==========================================
# CAMPAIGN
# ==========================================
class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    industry_id = Column(Integer, ForeignKey("industry_configs.id"))
    target_quantity = Column(Integer, default=100)
    min_quality_score = Column(Integer, default=80)
    status = Column(String(50), default="draft")
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    industry = relationship("IndustryConfig")

class CampaignLocation(Base):
    __tablename__ = "campaign_locations"
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    country = Column(String(100))
    region_state = Column(String(100))
    county = Column(String(100))
    city = Column(String(100))
    postal_code = Column(String(50))
    latitude = Column(Float)
    longitude = Column(Float)
    radius_km = Column(Float)

class JobRun(Base):
    __tablename__ = "job_runs"
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    stage = Column(String(100))
    status = Column(String(50))
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    metrics = Column(JSON, default=dict)

# ==========================================
# BUSINESS / CORE
# ==========================================
class Business(Base):
    __tablename__ = "businesses"
    id = Column(Integer, primary_key=True, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    name = Column(String(255), nullable=False)
    normalized_name = Column(String(255))
    industry = Column(String(255))
    sub_industry = Column(String(255))
    
    country = Column(String(100))
    state_province = Column(String(100))
    county = Column(String(100))
    city = Column(String(100))
    postal_code = Column(String(50))
    address = Column(Text)
    latitude = Column(Float)
    longitude = Column(Float)
    
    primary_phone = Column(String(100))
    website_url = Column(String(2048))
    website_domain = Column(String(255), index=True)
    google_place_id = Column(String(255))
    rating = Column(Float)
    review_count = Column(Integer)
    hours = Column(JSON)
    
    status = Column(String(50), default="raw")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class BusinessSource(Base):
    __tablename__ = "business_sources"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    source = Column(String(100)) # e.g. DataForSEO
    source_id = Column(String(255))
    source_url = Column(String(2048))
    collected_at = Column(DateTime(timezone=True), server_default=func.now())

# ==========================================
# WEBSITE INTELLIGENCE
# ==========================================
class Website(Base):
    __tablename__ = "websites"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    url = Column(String(2048), nullable=False)
    is_live = Column(Boolean)
    has_ssl = Column(Boolean)
    cms = Column(String(100))
    framework = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class WebsitePage(Base):
    __tablename__ = "website_pages"
    id = Column(Integer, primary_key=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id"))
    url = Column(String(2048))
    page_type = Column(String(100)) # homepage, contact, booking, about
    title = Column(String(500))
    status_code = Column(Integer)
    crawled_at = Column(DateTime(timezone=True), server_default=func.now())

class WebsiteTechnology(Base):
    __tablename__ = "website_technologies"
    id = Column(Integer, primary_key=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id"))
    technology = Column(String(255)) # e.g., Google Analytics, Calendly
    category = Column(String(100)) # analytics, booking, payment
    confidence = Column(Float)

class WebsiteScreenshot(Base):
    __tablename__ = "website_screenshots"
    id = Column(Integer, primary_key=True, index=True)
    website_page_id = Column(Integer, ForeignKey("website_pages.id"))
    viewport_type = Column(String(50)) # desktop, mobile
    s3_key_or_path = Column(String(2048))
    captured_at = Column(DateTime(timezone=True), server_default=func.now())

class WebsiteAudit(Base):
    __tablename__ = "website_audits"
    id = Column(Integer, primary_key=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id"))
    
    # Audit Flags & Scores
    mobile_responsive = Column(Boolean)
    horizontal_overflow = Column(Boolean)
    
    performance_score = Column(Integer)
    seo_score = Column(Integer)
    desktop_ux_score = Column(Integer)
    mobile_ux_score = Column(Integer)
    accessibility_score = Column(Integer)
    
    # Conversion
    phone_cta = Column(Boolean)
    contact_form = Column(Boolean)
    quote_form = Column(Boolean)
    live_chat = Column(Boolean)
    whatsapp = Column(Boolean)
    sticky_cta = Column(Boolean)
    
    # Booking
    booking_detected = Column(Boolean)
    booking_provider = Column(String(100))
    
    # Ecom
    ecommerce_detected = Column(Boolean)
    cart_detected = Column(Boolean)
    checkout_detected = Column(Boolean)
    
    audited_at = Column(DateTime(timezone=True), server_default=func.now())

class WebsiteEvidence(Base):
    __tablename__ = "website_evidence"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    source_page_id = Column(Integer, ForeignKey("website_pages.id"), nullable=True)
    screenshot_id = Column(Integer, ForeignKey("website_screenshots.id"), nullable=True)
    evidence_type = Column(String(100)) # e.g. mobile_cta_below_fold, no_booking_system
    finding = Column(Text)
    observed_value = Column(Text)
    confidence = Column(Float)
    collected_at = Column(DateTime(timezone=True), server_default=func.now())

class SocialProfile(Base):
    __tablename__ = "social_profiles"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    platform = Column(String(50)) # facebook, instagram, linkedin
    profile_url = Column(String(2048))
    followers = Column(Integer, nullable=True)

# ==========================================
# PEOPLE
# ==========================================
class DecisionMaker(Base):
    __tablename__ = "decision_makers"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    first_name = Column(String(100))
    last_name = Column(String(100))
    title = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    mobile = Column(String(50))
    linkedin_url = Column(String(2048))
    contact_type = Column(String(50)) # professional, personal
    verification_status = Column(String(50)) # verified, risky, unknown
    confidence = Column(Float)
    source = Column(String(100)) # e.g. snovio, proxycurl, website_crawl, public_search
    source_url = Column(String(2048)) # Specific URL where the contact was found (e.g. LinkedIn or About page)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# ==========================================
# INTELLIGENCE
# ==========================================
class Score(Base):
    __tablename__ = "scores"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    commercial_score = Column(Integer)
    data_confidence = Column(Integer)
    grade = Column(String(10)) # A+, A, B, C, Reject
    
    # Components
    business_fit = Column(Integer)
    digital_gap = Column(Integer)
    offer_fit = Column(Integer)
    buying_intent = Column(Integer)
    contactability = Column(Integer)
    
    score_version = Column(String(50))
    evidence_ids = Column(JSON) # List of Evidence IDs supporting this score
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Opportunity(Base):
    __tablename__ = "opportunities"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    primary_problem = Column(Text)
    problems = Column(JSON)
    recommended_offer_id = Column(Integer, ForeignKey("devacia_offers.id"), nullable=True)
    recommended_offer = Column(String(255))
    ticket_low = Column(Integer)
    ticket_high = Column(Integer)
    outreach_angle = Column(Text)
    ai_reasoning = Column(Text)
    confidence = Column(String(50))
    evidence_ids = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
class AIAnalysis(Base):
    __tablename__ = "ai_analyses"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=True)
    model_name = Column(String(100))
    prompt_template = Column(Text)
    raw_response = Column(Text)
    parsed_output = Column(JSON)
    tokens_used = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    business = relationship("Business")

# ==========================================
# CRM WORKSPACE
# ==========================================
class CRMLead(Base):
    """Workspace-specific CRM state for a discovered or imported business."""
    __tablename__ = "crm_leads"
    id = Column(Integer, primary_key=True, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, unique=True, index=True)
    stage = Column(String(50), nullable=False, default="new", index=True)
    owner_name = Column(String(255))
    tags = Column(JSON, default=list)
    source = Column(String(50), nullable=False, default="campaign")
    next_follow_up_at = Column(DateTime(timezone=True))
    last_contacted_at = Column(DateTime(timezone=True))
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class CRMActivity(Base):
    """A simple, append-only activity timeline for the in-app CRM."""
    __tablename__ = "crm_activities"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    activity_type = Column(String(50), nullable=False, default="note")
    body = Column(Text, nullable=False)
    created_by = Column(String(100), default="Workspace")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# ==========================================
# LEGACY CRM & EXPORT
# ==========================================
class CRMNote(Base):
    __tablename__ = "crm_notes"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    note_text = Column(Text)
    created_by = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Export(Base):
    __tablename__ = "exports"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    format = Column(String(50)) # csv, xlsx, google_sheets
    status = Column(String(50))
    file_url = Column(String(2048))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
