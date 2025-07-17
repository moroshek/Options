name: "Contact Enrichment System: Automated Research with Secure Data Pipeline"
description: |

## Purpose
Build a fully automated system that processes contact CSV files, performs web research on individuals, enriches data with AI-generated structured tags, stores in PostgreSQL with JSONB, and provides secure Google Sheets interface for customers while keeping research methods private.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md

---

## Goal
Create a production-ready contact enrichment pipeline that automatically researches individuals from CSV files, generates structured JSONB tags for microtargeting, stores data securely in PostgreSQL, and provides customers with a sanitized Google Sheets interface while keeping proprietary research methods hidden.

## Why
- **Business value**: Enables precise audience segmentation and personalized outreach at scale
- **Customer value**: Provides enriched contact data without exposing research methodology
- **Competitive advantage**: Proprietary tagging system remains private while delivering value
- **Automation**: Eliminates manual research labor for contact enrichment

## What
An automated system where:
- CSV files trigger n8n workflows hosted on Google Compute Engine
- Web research performed via Google Search API and Jina Reader (or WebSailor if deployed)
- AI models (GPT-4/Claude) extract structured tags in JSONB format
- PostgreSQL stores both raw research and structured data
- Security views hide proprietary data from customers
- Google Sheets provides real-time customer interface
- Internal queries enable precise microtargeting

### Success Criteria
- [ ] CSV upload triggers automatic processing workflow
- [ ] Web research returns relevant information per contact
- [ ] AI generates valid JSONB structured tags
- [ ] PostgreSQL stores data with proper indexing
- [ ] Security views prevent access to proprietary data
- [ ] Google Sheets syncs daily with customer view
- [ ] Microtargeting queries return accurate segments
- [ ] System handles 1000+ contacts efficiently

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://docs.n8n.io/workflows/
  why: Core workflow creation patterns, nodes, error handling
  
- url: https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.csv/
  why: CSV file processing patterns and batch operations
  
- url: https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.postgres/
  why: PostgreSQL node configuration and JSONB operations
  
- url: https://www.postgresql.org/docs/current/datatype-json.html
  why: JSONB data type, operators, indexing strategies
  
- url: https://www.postgresql.org/docs/current/ddl-views.html
  why: Creating security abstraction views
  
- url: https://developers.google.com/apps-script/guides/jdbc
  why: Google Apps Script JDBC connection to PostgreSQL
  
- url: https://developers.google.com/apps-script/guides/triggers/installable
  why: Time-driven triggers for automated sync
  
- url: https://github.com/Alibaba-NLP/WebAgent/tree/main/WebSailor
  why: WebSailor is an AI agent model for web research, not a simple API
  
- url: https://serpapi.com/
  why: Google Search API needed for WebSailor/WebDancer
  
- url: https://jina.ai/reader/
  why: Jina Reader API for web content extraction
  
- file: examples/csv_sample.csv
  why: Expected CSV input format
  
- file: examples/json_schema.json
  why: JSONB structure for contact tags
  
- file: examples/database_schema.sql
  why: Table and view definitions
```

### Current Codebase tree
```bash
.
├── examples/
├── PRPs/
│   └── templates/
│       └── prp_base.md
├── INITIAL.md
├── CLAUDE.md
├── TASK.md
└── README.md
```

### Desired Codebase tree with files to be added
```bash
.
├── examples/
│   ├── csv_sample.csv              # Sample input CSV
│   ├── json_schema.json            # JSONB tag structure
│   ├── n8n_workflow.json           # Complete n8n workflow
│   ├── database_schema.sql         # PostgreSQL setup
│   ├── query_examples.sql          # Microtargeting queries
│   └── apps_script.js              # Google Sheets sync
├── src/
│   ├── __init__.py                 # Package init
│   ├── enrichment/
│   │   ├── __init__.py
│   │   ├── processor.py            # Contact processing logic
│   │   ├── websailor_client.py     # WebSailor integration
│   │   ├── ai_tagger.py            # AI tagging service
│   │   └── models.py               # Pydantic models
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py           # Database connection pool
│   │   ├── queries.py              # Query builders
│   │   └── migrations/             # Database migrations
│   └── utils/
│       ├── __init__.py
│       ├── validators.py           # Data validation
│       └── logger.py               # Logging configuration
├── tests/
│   ├── __init__.py
│   ├── test_processor.py           # Processing tests
│   ├── test_websailor.py           # WebSailor integration tests
│   ├── test_ai_tagger.py           # Tagging tests
│   ├── test_database.py            # Database operations tests
│   └── test_integration.py         # End-to-end tests
├── scripts/
│   ├── setup_database.py           # Database initialization
│   ├── test_sync.py                # Test Google Sheets sync
│   └── generate_sample_data.py     # Create test data
├── config/
│   ├── __init__.py
│   ├── settings.py                 # Environment configuration
│   └── prompts.py                  # AI prompts for tagging
├── deployment/
│   ├── n8n_config.json             # n8n instance configuration
│   ├── setup_gce.sh                # Google Compute Engine setup
│   └── nginx.conf                  # Reverse proxy config
├── .env.example                    # Environment variables template
├── requirements.txt                # Python dependencies
├── README.md                       # Comprehensive documentation
└── Makefile                        # Common commands
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: n8n webhook URLs must be whitelisted in GCE firewall
# CRITICAL: WebSailor is an AI model requiring deployment, not a simple API
# CRITICAL: Requires Google Search API (SerpAPI) and Jina Reader API keys
# CRITICAL: PostgreSQL JSONB queries use specific operators (@>, ->, ->>, ?)
# CRITICAL: Google Apps Script has 6-minute execution time limit
# CRITICAL: JDBC in Apps Script requires Cloud SQL proxy for external IPs
# CRITICAL: AI models may return inconsistent JSON - validate structure
# CRITICAL: CSV files may have encoding issues - handle UTF-8 BOM
# CRITICAL: Google Sheets API has quota limits - batch operations required
# CRITICAL: Consider using GPT-4/Claude API as simpler alternative to WebSailor deployment
```

## Implementation Blueprint

### Data models and structure

```python
# models.py - Core data structures
from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ContactInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    company: str = Field(..., max_length=255)
    
    @validator('name')
    def clean_name(cls, v):
        return v.strip().title()

class ProfessionalRole(BaseModel):
    title: str
    company: str
    start_date: Optional[str] = None
    duration_years: Optional[int] = None

class ContactTags(BaseModel):
    identity: Dict[str, str] = Field(default_factory=dict)
    professional_profile: Dict[str, Any] = Field(default_factory=dict)
    attributes: Dict[str, List[str]] = Field(default_factory=dict)
    online_presence: Dict[str, str] = Field(default_factory=dict)
    financial_indicators: Dict[str, Any] = Field(default_factory=dict)
    personal_interests: Dict[str, List[str]] = Field(default_factory=dict)
    network_influence: Dict[str, Any] = Field(default_factory=dict)
    life_stage: Dict[str, Any] = Field(default_factory=dict)
    values_beliefs: Dict[str, Any] = Field(default_factory=dict)
    profile_image_url: Optional[str] = None
    system_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "identity": {
                    "full_name": "John Doe",
                    "location": "Minneapolis, MN",
                    "email": "john.doe@example.com"
                },
                "professional_profile": {
                    "current_role": {
                        "title": "CEO & Founder",
                        "company": "Innovate Corp"
                    }
                },
                "attributes": {
                    "skills": ["Python", "Leadership"],
                    "interests": ["AI", "Startups"]
                },
                "financial_indicators": {
                    "estimated_income_range": "$150k-$250k",
                    "wealth_signals": ["startup_founder", "angel_investor"]
                },
                "personal_interests": {
                    "hobbies": ["golf", "sailing"],
                    "causes": ["climate_tech", "education"]
                },
                "network_influence": {
                    "conference_speaker": ["TechCrunch Disrupt 2023", "SaaStr 2024"],
                    "published_articles": 12,
                    "board_positions": ["Tech Nonprofit Board Member"],
                    "professional_associations": ["YPO", "Entrepreneurs' Organization"],
                    "patents": 2
                },
                "life_stage": {
                    "recent_job_change": "2023-03-01",
                    "company_milestones": ["Series B - $50M", "100 employees"],
                    "education_updates": ["Executive MBA - 2022"],
                    "family_indicators": ["married", "2 children"],
                    "property_records": ["Purchased $1.2M home - 2023"]
                },
                "values_beliefs": {
                    "political_contributions": [
                        {"recipient": "Candidate Name", "amount": 2800, "year": 2024}
                    ],
                    "charity_involvement": ["Red Cross Board", "Local Food Bank Donor"]
                },
                "profile_image_url": "https://media.linkedin.com/example.jpg"
            }
        }

class EnrichedContact(BaseModel):
    id: int
    full_name: str
    email: str
    company: str
    tags: ContactTags
    raw_research: str
    created_at: datetime
    updated_at: datetime
```

### List of tasks to be completed

```yaml
Task 1: Setup Project Structure and Configuration
CREATE config/settings.py:
  - PATTERN: Use pydantic-settings for type-safe config
  - Load all environment variables
  - Validate required credentials exist
  
CREATE .env.example:
  - Include all configuration with descriptions
  - Group by service (Database, APIs, Google)

Task 2: Create Database Schema and Migrations
CREATE examples/database_schema.sql:
  - Main contacts table with JSONB tags column
  - Security view hiding tags and raw_research
  - Indexes on JSONB fields for query performance
  
CREATE scripts/setup_database.py:
  - Connect to Cloud SQL PostgreSQL
  - Execute schema creation
  - Verify indexes and views

Task 3: Implement Swappable Research Backend
CREATE src/enrichment/research_backends.py:
  - PATTERN: Abstract base class for swappable backends
  - SimpleAPIBackend: Google Search + Jina Reader + GPT-4
  - WebSailorBackend: For future WebSailor deployment
  - Profile image extraction capability
  - Handle rate limiting with exponential backoff
  - Parse research results into structured format
  - Log all API interactions for debugging

Task 4: Implement AI Tagging Service
CREATE src/enrichment/ai_tagger.py:
  - PATTERN: Use OpenAI/Claude API with structured output
  - Validate JSON response matches ContactTags schema
  - Handle malformed responses with retry
  - Include prompt engineering for consistency

Task 5: Build Contact Processing Pipeline
CREATE src/enrichment/processor.py:
  - Read CSV with pandas, handle encoding issues
  - Process contacts in configurable batches
  - Orchestrate WebSailor + AI tagging
  - Store results in PostgreSQL with transactions

Task 6: Create n8n Workflow Configuration
CREATE examples/n8n_workflow.json:
  - Webhook trigger for CSV upload
  - CSV Read node with error handling
  - Loop through contacts with rate limiting
  - HTTP Request nodes for research backend
  - Image download and storage node
  - PostgreSQL insert with error catching
  - Email notification on completion

Task 7: Implement Google Sheets Integration
CREATE examples/apps_script.js:
  - JDBC connection to Cloud SQL
  - Query customer_contacts_view only
  - Batch update sheet for performance
  - Time-driven trigger for daily sync
  - Error logging to stackdriver

Task 8: Create Microtargeting Query Examples
CREATE examples/query_examples.sql:
  - Find contacts by skills/interests
  - Location-based filtering
  - Professional role queries
  - Complex multi-criteria searches
  - Performance-optimized patterns

Task 9: Build Comprehensive Test Suite
CREATE tests/:
  - Unit tests for each component
  - Integration tests with mocked APIs
  - Database transaction tests
  - CSV parsing edge cases
  - JSONB query validation

Task 10: Create Deployment and Documentation
CREATE deployment/:
  - GCE instance setup script
  - n8n installation and configuration
  - Nginx reverse proxy for security
  
UPDATE README.md:
  - Architecture diagram
  - Complete setup instructions
  - API key configuration
  - Troubleshooting guide
```

### Per task pseudocode

```python
# Task 3: Swappable Research Backend
import httpx
import asyncio
from typing import Dict, List, Optional
from abc import ABC, abstractmethod
import backoff
from serpapi import GoogleSearch

class ResearchBackend(ABC):
    @abstractmethod
    async def research_person(self, name: str, company: str, email: str) -> Dict:
        """Research a person and return comprehensive profile data."""
        pass
    
    @abstractmethod
    async def extract_profile_image(self, profile_url: str) -> Optional[str]:
        """Extract profile image from a URL, return base64 or URL."""
        pass

class SimpleAPIBackend(ResearchBackend):
    def __init__(self, serp_api_key: str, jina_api_key: str):
        self.serp_api_key = serp_api_key
        self.jina_api_key = jina_api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    @backoff.on_exception(
        backoff.expo,
        (httpx.HTTPStatusError, httpx.TimeoutException),
        max_tries=3
    )
    async def research_person(self, name: str, company: str, email: str) -> Dict:
        """Research individual using Google Search + Jina Reader."""
        # Step 1: Multi-faceted search
        queries = [
            f'"{name}" "{company}" LinkedIn profile',
            f'"{name}" "{company}" conference speaker',
            f'"{name}" published articles blog posts',
            f'"{name}" board member director positions',
            f'"{name}" site:fec.gov',  # CRITICAL: FEC political contributions
            f'"{name}" "{company}" funding round acquisition',
            f'"{name}" property records real estate',
            f'"{name}" charity nonprofit involvement'
        ]
        
        # Aggregate results from all queries
        all_results = []
        research_texts = []
        profile_image = None
        
        for query in queries:
            search = GoogleSearch({
                "q": query,
                "api_key": self.serp_api_key,
                "num": 5
            })
            results = search.get_dict()
            all_results.extend(results.get("organic_results", []))
        
        # Step 2: Extract content and look for profile images
        for result in all_results[:10]:  # Process top 10 results
            url = result.get("link", "")
            if url:
                # Check for LinkedIn profile
                if "linkedin.com/in/" in url and not profile_image:
                    profile_image = await self.extract_profile_image(url)
                
                # Extract content
                content = await self._extract_content(url)
                if content:
                    research_texts.append(content)
        
        return {
            "queries": queries,
            "sources": [r.get("link") for r in all_results[:10]],
            "text": "\n\n".join(research_texts),
            "profile_image": profile_image
        }
    
    async def _extract_content(self, url: str) -> str:
        """Extract clean text from URL using Jina Reader."""
        jina_url = f"https://r.jina.ai/{url}"
        headers = {"Authorization": f"Bearer {self.jina_api_key}"}
        
        try:
            response = await self.client.get(jina_url, headers=headers)
            response.raise_for_status()
            return response.text[:5000]  # Limit content length
        except Exception as e:
            logger.warning(f"Failed to extract {url}: {e}")
            return ""
    
    async def extract_profile_image(self, profile_url: str) -> Optional[str]:
        """Extract profile image from LinkedIn or other profile."""
        # Use Jina Reader to get the page
        content = await self._extract_content(profile_url)
        
        # Parse for og:image meta tag or profile photo
        # In production, use BeautifulSoup or similar
        import re
        image_pattern = r'<meta property="og:image" content="([^"]+)"'
        match = re.search(image_pattern, content)
        
        if match:
            image_url = match.group(1)
            # Either return URL or download and base64 encode
            return image_url
        return None

class WebSailorBackend(ResearchBackend):
    """Future implementation for WebSailor deployment."""
    
    async def research_person(self, name: str, company: str, email: str) -> Dict:
        # WebSailor can do multi-hop reasoning
        # It would naturally find LinkedIn, then blog, then conference talks
        # Building a comprehensive profile in one go
        raise NotImplementedError("WebSailor deployment coming in Phase 2")
    
    async def extract_profile_image(self, profile_url: str) -> Optional[str]:
        # WebSailor would handle this as part of its navigation
        raise NotImplementedError("WebSailor deployment coming in Phase 2")

# Task 4: AI Tagging
class AITagger:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model
        
    async def extract_tags(self, research_text: str, contact: ContactInput) -> ContactTags:
        """Extract structured tags from research text."""
        # PATTERN: Use function calling for structured output
        prompt = f"""
        Analyze this research about {contact.name} at {contact.company}.
        Extract comprehensive information including:
        
        Professional Profile:
        - Current and past roles with dates
        - Estimated income based on role, company size, location
        - Company funding status and milestones
        
        Network & Influence:
        - Conference speaking engagements
        - Published articles or blog posts
        - Board positions or advisory roles
        - Professional associations (YPO, EO, etc.)
        - Patents or research papers
        
        Life Stage Indicators:
        - Recent job changes or promotions
        - Education updates or certifications
        - Family status if mentioned
        - Property purchases or real estate
        
        Values & Beliefs (CRITICAL):
        - Political contributions from FEC records (amount, recipient, year)
        - Charitable involvement and causes
        - Social causes they champion
        
        Financial Indicators:
        - Travel patterns (luxury destinations, business class)
        - Restaurant or venue mentions
        - Investment activity if mentioned
        
        Return as JSON matching this schema:
        {ContactTags.schema_json(indent=2)}
        
        Research text:
        {research_text}
        """
        
        # GOTCHA: Validate response matches schema
        response = await self._call_ai(prompt)
        
        try:
            tags_dict = json.loads(response)
            return ContactTags(**tags_dict)
        except (json.JSONDecodeError, ValidationError) as e:
            # PATTERN: Retry with more specific prompt
            logger.warning(f"Invalid JSON from AI: {e}")
            raise

# Task 5: Contact Processor
class ContactProcessor:
    async def process_batch(self, contacts: List[ContactInput]) -> List[EnrichedContact]:
        """Process contacts with rate limiting."""
        enriched = []
        
        # PATTERN: Process in chunks to respect rate limits
        for contact in contacts:
            try:
                # Research with swappable backend
                research = await self.research_backend.research_person(
                    contact.name, 
                    contact.company,
                    contact.email
                )
                
                # Extract tags with AI
                tags = await self.tagger.extract_tags(
                    research["text"], 
                    contact
                )
                
                # Store in database
                enriched_contact = await self.db.store_contact(
                    contact, tags, research["text"]
                )
                enriched.append(enriched_contact)
                
                # CRITICAL: Rate limit = 100/hour
                await asyncio.sleep(36)  # 36 seconds = 100 per hour
                
            except Exception as e:
                logger.error(f"Failed to process {contact.name}: {e}")
                # Continue processing other contacts
                continue
        
        return enriched
```

### Database Schema
```sql
-- Main contacts table
CREATE TABLE contacts (
    id SERIAL PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    company TEXT,
    tags JSONB NOT NULL,
    raw_research TEXT,
    profile_image_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for JSONB queries
CREATE INDEX idx_contacts_tags ON contacts USING GIN (tags);
CREATE INDEX idx_contacts_skills ON contacts USING GIN ((tags->'attributes'->'skills'));
CREATE INDEX idx_contacts_interests ON contacts USING GIN ((tags->'personal_interests'->'hobbies'));
CREATE INDEX idx_contacts_location ON contacts USING BTREE ((tags->'identity'->>'location'));
CREATE INDEX idx_contacts_political ON contacts USING GIN ((tags->'values_beliefs'->'political_contributions'));
CREATE INDEX idx_contacts_influence ON contacts USING GIN ((tags->'network_influence'));

-- Security view for customers (hides proprietary data)
CREATE VIEW customer_contacts_view AS
SELECT id, full_name, email, company, created_at
FROM contacts;

-- Internal view for app development
CREATE VIEW internal_app_view AS
SELECT 
    id, 
    full_name, 
    email, 
    company,
    profile_image_url,
    tags->'identity'->>'location' as location,
    tags->'professional_profile'->'current_role'->>'title' as current_title,
    tags->'financial_indicators'->>'estimated_income_range' as income_range
FROM contacts;

-- Example microtargeting queries
-- Find high-income founders interested in AI
SELECT full_name, email, profile_image_url 
FROM contacts
WHERE tags->'professional_profile'->'current_role'->>'title' ILIKE '%founder%'
AND tags->'attributes'->'interests' @> '["Artificial Intelligence"]'
AND tags->'financial_indicators'->>'estimated_income_range' ~ '\$[2-9][0-9]{2}k';

-- Find people with luxury hobbies
SELECT full_name, email, tags->'personal_interests'->'hobbies' as hobbies
FROM contacts
WHERE tags->'personal_interests'->'hobbies' ?| array['golf', 'sailing', 'wine_collecting'];

-- CRITICAL: Find political donors above $1000
SELECT full_name, email, 
       tags->'values_beliefs'->'political_contributions' as contributions
FROM contacts
WHERE jsonb_array_length(tags->'values_beliefs'->'political_contributions') > 0
AND EXISTS (
    SELECT 1 FROM jsonb_array_elements(tags->'values_beliefs'->'political_contributions') as contrib
    WHERE (contrib->>'amount')::int > 1000
);

-- Find conference speakers with board positions
SELECT full_name, email, 
       tags->'network_influence'->'conference_speaker' as speaking,
       tags->'network_influence'->'board_positions' as boards
FROM contacts
WHERE jsonb_array_length(tags->'network_influence'->'conference_speaker') > 0
AND jsonb_array_length(tags->'network_influence'->'board_positions') > 0;

-- Target recent job changers at funded companies
SELECT full_name, email, company,
       tags->'life_stage'->>'recent_job_change' as job_change_date
FROM contacts
WHERE tags->'life_stage'->>'recent_job_change' > '2023-01-01'
AND tags->'life_stage'->'company_milestones' @> '["Series B"]';
```

### Integration Points
```yaml
DATABASE:
  - connection: "postgresql://user:pass@/database?host=/cloudsql/project:region:instance"
  - pool_size: 20
  - migrations: src/database/migrations/
  
N8N_WORKFLOW:
  - webhook_url: "https://n8n.yourdomain.com/webhook/contact-enrichment"
  - error_webhook: "https://n8n.yourdomain.com/webhook/enrichment-errors"
  - batch_size: 10
  
GOOGLE_SHEETS:
  - spreadsheet_id: "YOUR_SHEET_ID"
  - range: "Contacts!A:C"
  - service_account: "./credentials/sheets-service-account.json"
  
API_KEYS:
  - serp_api: "SERP_API_KEY"
  - jina_api: "JINA_API_KEY"
  - openai: "OPENAI_API_KEY"
  - google_cloud: "GOOGLE_APPLICATION_CREDENTIALS"
  
STORAGE:
  - profile_images: "gs://your-bucket/profile-images/"  # Or S3, R2
  - image_cdn: "https://cdn.yourdomain.com/profiles/"
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
black src/ tests/ --line-length=100
ruff check src/ tests/ --fix
mypy src/ --strict

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests
```python
# test_processor.py
async def test_csv_parsing():
    """Test CSV parsing handles various formats"""
    processor = ContactProcessor()
    
    # Test UTF-8 BOM handling
    csv_with_bom = b'\xef\xbb\xbf' + b'name,email,company\nJohn,john@example.com,ACME'
    contacts = processor.parse_csv(csv_with_bom)
    assert len(contacts) == 1
    assert contacts[0].name == "John"

async def test_rate_limiting():
    """Test rate limiter prevents API overwhelm"""
    processor = ContactProcessor()
    contacts = [ContactInput(...) for _ in range(5)]
    
    start_time = time.time()
    await processor.process_batch(contacts)
    elapsed = time.time() - start_time
    
    # Should take at least 180 seconds for 5 contacts (36s each)
    assert elapsed >= 180

# test_database.py
def test_jsonb_queries():
    """Test JSONB query patterns work correctly"""
    # Insert test data
    contact = EnrichedContact(
        tags={"attributes": {"skills": ["Python", "AI"]}}
    )
    
    # Test skill search
    results = db.query("""
        SELECT * FROM contacts 
        WHERE tags->'attributes'->'skills' @> '["Python"]'
    """)
    assert len(results) == 1

# test_integration.py
async def test_end_to_end():
    """Test complete pipeline from CSV to database"""
    # Upload test CSV
    csv_content = "name,email,company\nTest User,test@example.com,Test Corp"
    
    # Process through pipeline
    result = await process_csv(csv_content)
    
    # Verify in database
    contact = await db.get_contact_by_email("test@example.com")
    assert contact.tags.identity["full_name"] == "Test User"
    assert "skills" in contact.tags.attributes
```

```bash
# Run tests iteratively until passing:
pytest tests/ -v --cov=src --cov-report=term-missing

# For specific test debugging:
pytest tests/test_processor.py::test_rate_limiting -vvs
```

### Level 3: Integration Test
```bash
# 1. Test database connection
python scripts/setup_database.py --test

# 2. Test n8n workflow
curl -X POST https://n8n.yourdomain.com/webhook-test/contact-enrichment \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# 3. Process sample CSV
python -m src.enrichment.processor examples/csv_sample.csv

# 4. Verify Google Sheets sync
python scripts/test_sync.py

# Expected: All components connect and data flows through pipeline
```

## Final Validation Checklist
- [ ] All tests pass: `pytest tests/ -v`
- [ ] No linting errors: `ruff check src/`
- [ ] No type errors: `mypy src/ --strict`
- [ ] Database schema created with indexes
- [ ] Security view hides proprietary columns
- [ ] n8n workflow processes CSV successfully
- [ ] WebSailor returns research data
- [ ] AI generates valid JSONB tags
- [ ] Google Sheets shows customer data only
- [ ] Microtargeting queries return correct results
- [ ] Rate limiting prevents API errors
- [ ] Error handling logs issues appropriately
- [ ] README includes complete setup guide

---

## Anti-Patterns to Avoid
- ❌ Don't expose tags or raw_research in customer view
- ❌ Don't skip CSV encoding validation
- ❌ Don't ignore rate limits (ban risk)
- ❌ Don't store API keys in code
- ❌ Don't use synchronous code in async context
- ❌ Don't trust AI JSON without validation
- ❌ Don't forget JSONB indexes (query performance)
- ❌ Don't exceed Google Sheets API quotas
- ❌ Don't commit credentials or .env files

## Confidence Score: 8/10

High confidence due to:
- Well-documented APIs and libraries
- Clear security requirements
- Established patterns for data pipelines
- Comprehensive validation approach

Moderate uncertainty on:
- WebSailor deployment timing (Phase 2 implementation)
- Profile image extraction reliability from various sources
- First-time n8n deployment complexity
- Google Apps Script JDBC connection quirks

Migration path provided for seamless transition from SimpleAPIBackend to WebSailorBackend when ready.

The system is achievable with the provided context and validation gates ensure quality implementation.