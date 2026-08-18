from sqlalchemy import Column, Integer, String, Boolean, Float, Text, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

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

class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    country = Column(String(100), nullable=False)
    state_province = Column(String(100))
    cities = Column(JSON, default=list)
    industry_id = Column(Integer, ForeignKey("industry_configs.id"))
    target_quantity = Column(Integer, default=100)
    min_quality_score = Column(Integer, default=80)
    status = Column(String(50), default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    industry = relationship("IndustryConfig")

class Business(Base):
    __tablename__ = "businesses"
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    name = Column(String(255), nullable=False)
    normalized_name = Column(String(255))
    domain = Column(String(255))
    phone = Column(String(50))
    company_email = Column(String(255))
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    place_id = Column(String(255))
    google_rating = Column(Float)
    review_count = Column(Integer)
    source_metadata = Column(JSON, default=dict) # For deduplication
    status = Column(String(50), default="raw")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Website(Base):
    __tablename__ = "websites"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    url = Column(String(2048), nullable=False)
    is_live = Column(Boolean)
    has_ssl = Column(Boolean)
    technology_stack = Column(JSON, default=list) # WordPress, Shopify, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class WebsiteAudit(Base):
    __tablename__ = "website_audits"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    mobile_responsive = Column(Boolean)
    performance_score = Column(Integer)
    seo_score = Column(Integer)
    ux_score = Column(Integer)
    booking_detected = Column(Boolean)
    ecommerce_detected = Column(Boolean)
    raw_audit_data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SocialProfile(Base):
    __tablename__ = "social_profiles"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    platform = Column(String(50)) # facebook, instagram, linkedin
    profile_url = Column(String(2048))
    followers = Column(Integer, nullable=True)

class DecisionMaker(Base):
    __tablename__ = "decision_makers"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    first_name = Column(String(100))
    last_name = Column(String(100))
    title = Column(String(255))
    email = Column(String(255))
    email_status = Column(String(50)) # verified, risky, unknown
    phone = Column(String(50))
    linkedin_url = Column(String(2048))
    source = Column(String(100)) # e.g. Apollo
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Contact(Base):
    # Deprecated/Alias for backward compatibility with frontend, use DecisionMaker moving forward or map it.
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(255))
    title = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    source_type = Column(String(100), nullable=False) # e.g. screenshot, html_crawler, lighthouse
    evidence_text = Column(Text)
    evidence_url = Column(String(2048)) # For screenshot paths
    confidence = Column(Float)
    page_url = Column(String(2048))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Score(Base):
    __tablename__ = "scores"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    total_score = Column(Integer)
    business_fit = Column(Integer)
    website_gap = Column(Integer)
    ux_ui_gap = Column(Integer)
    conversion_gap = Column(Integer)
    offer_fit = Column(Integer)
    contactability = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Opportunity(Base):
    __tablename__ = "opportunities"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    primary_problem = Column(Text)
    outreach_angle = Column(Text)
    recommended_offer_id = Column(Integer, ForeignKey("devacia_offers.id"))
    estimated_value = Column(String(100))
    ai_summary = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    business = relationship("Business")
