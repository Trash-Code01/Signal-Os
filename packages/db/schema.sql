CREATE TABLE industry_configs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    signals JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE devacia_offers (
    id SERIAL PRIMARY KEY,
    industry_id INTEGER REFERENCES industry_configs(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE campaigns (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(100) NOT NULL,
    state_province VARCHAR(100),
    cities JSONB NOT NULL DEFAULT '[]',
    industry_id INTEGER REFERENCES industry_configs(id),
    target_quantity INTEGER DEFAULT 100,
    min_quality_score INTEGER DEFAULT 80,
    status VARCHAR(50) DEFAULT 'draft',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE search_queries (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER REFERENCES campaigns(id),
    query VARCHAR(255) NOT NULL,
    provider VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE businesses (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER REFERENCES campaigns(id),
    name VARCHAR(255) NOT NULL,
    normalized_name VARCHAR(255),
    domain VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    place_id VARCHAR(255),
    source_metadata JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'raw',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE websites (
    id SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    url VARCHAR(2048) NOT NULL,
    is_live BOOLEAN,
    has_ssl BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE website_audits (
    id SERIAL PRIMARY KEY,
    website_id INTEGER REFERENCES websites(id),
    audit_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    raw_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE evidence (
    id SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    source_type VARCHAR(100) NOT NULL,
    evidence_text TEXT,
    confidence FLOAT,
    page_url VARCHAR(2048),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE scores (
    id SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    business_fit INTEGER DEFAULT 0,
    digital_gap INTEGER DEFAULT 0,
    offer_fit INTEGER DEFAULT 0,
    buying_intent INTEGER DEFAULT 0,
    contactability INTEGER DEFAULT 0,
    total_score INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE contacts (
    id SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    title VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    source VARCHAR(100),
    confidence FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE opportunities (
    id SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    primary_problem TEXT,
    recommended_offer_id INTEGER REFERENCES devacia_offers(id),
    suggested_project_range VARCHAR(100),
    outreach_angle TEXT,
    ai_reasoning TEXT,
    status VARCHAR(50) DEFAULT 'new',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
