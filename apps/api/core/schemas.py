from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# ==========================================
# CAMPAIGN
# ==========================================
class CampaignCreate(BaseModel):
    name: str
    country: str
    region_state: Optional[str] = None
    county: Optional[str] = None
    city: Optional[str] = None
    industry: str
    target_quantity: int = 100
    min_quality_score: int = 80
    settings: Optional[Dict[str, Any]] = None

class CampaignResponse(BaseModel):
    id: int
    name: str
    status: str
    target_quantity: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# ==========================================
# CORE CRM DTOs
# ==========================================
class DecisionMakerDTO(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    verification_status: Optional[str] = None
    confidence: Optional[float] = None
    source: Optional[str] = None

    class Config:
        from_attributes = True

class WebsiteEvidenceDTO(BaseModel):
    evidence_type: str
    finding: str
    observed_value: Optional[str] = None
    confidence: Optional[float] = None

    class Config:
        from_attributes = True

class BusinessLeadDTO(BaseModel):
    id: int
    name: str
    industry: Optional[str] = None
    country: Optional[str] = None
    state_province: Optional[str] = None
    county: Optional[str] = None
    city: Optional[str] = None
    primary_phone: Optional[str] = None
    website_url: Optional[str] = None
    
    # Intelligence
    commercial_score: Optional[int] = None
    data_confidence: Optional[int] = None
    grade: Optional[str] = None
    
    # Audit Flags
    mobile_responsive: Optional[bool] = None
    booking_detected: Optional[bool] = None
    ecommerce_detected: Optional[bool] = None
    cms: Optional[str] = None
    
    # Opportunity
    primary_problem: Optional[str] = None
    recommended_offer: Optional[str] = None
    ticket_low: Optional[int] = None
    ticket_high: Optional[int] = None
    outreach_angle: Optional[str] = None
    
    # Relations
    decision_makers: List[DecisionMakerDTO] = []
    evidence: List[WebsiteEvidenceDTO] = []

    class Config:
        from_attributes = True

class PaginatedLeadsResponse(BaseModel):
    total: int
    page: int
    size: int
    leads: List[BusinessLeadDTO]
