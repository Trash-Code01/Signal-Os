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
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    place_id = Column(String(255))
    source_metadata = Column(JSON, default=dict)
    status = Column(String(50), default="raw")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Website(Base):
    __tablename__ = "websites"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    url = Column(String(2048), nullable=False)
    is_live = Column(Boolean)
    has_ssl = Column(Boolean)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    source_type = Column(String(100), nullable=False)
    evidence_text = Column(Text)
    confidence = Column(Float)
    page_url = Column(String(2048))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Opportunity(Base):
    __tablename__ = "opportunities"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    primary_problem = Column(Text)
    outreach_angle = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    business = relationship("Business")

class Score(Base):
    __tablename__ = "scores"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    total_score = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(255))
    title = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
