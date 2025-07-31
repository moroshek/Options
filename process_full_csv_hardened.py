#!/usr/bin/env python3
"""
HARDENED Process CSV with complete enrichment pipeline
Includes:
- Cost tracking with budget limits
- Retry logic for API failures
- Enhanced rate limiting
- Database backup
- Better error handling
"""

import asyncio
import csv
import sqlite3
import sys
import os
import json
import shutil
import time
from datetime import datetime
import logging
from typing import List, Dict, Optional
from pathlib import Path
from collections import deque
from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from src.enrichment.complete_research_backend import CompleteResearchBackend
from src.database.local_db import LocalDatabase


class BudgetExceededError(Exception):
    """Raised when cost budget is exceeded"""
    pass


@dataclass
class CostTracker:
    """Track costs and enforce budget limits"""
    budget_limit: float = 30.00
    costs: Dict[str, float] = None
    
    def __post_init__(self):
        if self.costs is None:
            self.costs = {
                "perplexity": 0.0,
                "bright_data": 0.0,
                "linkedin": 0.0,
                "total_contacts": 0
            }
    
    def add_cost(self, service: str, amount: float):
        """Add cost and check budget"""
        self.costs[service] += amount
        total = self.get_total()
        if total > self.budget_limit:
            raise BudgetExceededError(f"Budget exceeded! Total: ${total:.2f}, Limit: ${self.budget_limit:.2f}")
    
    def add_contact(self):
        """Track contact processed"""
        self.costs["total_contacts"] += 1
        # Estimate costs based on typical usage
        self.add_cost("perplexity", 0.002)
        self.add_cost("bright_data", 0.015)
    
    def get_total(self) -> float:
        """Get total cost"""
        return sum(v for k, v in self.costs.items() if k != "total_contacts")
    
    def get_summary(self) -> str:
        """Get cost summary"""
        total = self.get_total()
        avg_per_contact = total / max(self.costs["total_contacts"], 1)
        return (f"💰 Cost Summary: Total ${total:.2f} | "
                f"Perplexity ${self.costs['perplexity']:.2f} | "
                f"Bright Data ${self.costs['bright_data']:.2f} | "
                f"Avg/contact ${avg_per_contact:.3f}")


class RateLimiter:
    """Enhanced rate limiting with sliding window"""
    def __init__(self, max_requests: int = 5, window_seconds: float = 1.0):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = deque()
    
    async def acquire(self):
        """Wait if necessary to respect rate limit"""
        now = time.time()
        
        # Remove old requests outside window
        while self.requests and self.requests[0] < now - self.window:
            self.requests.popleft()
        
        # If at limit, wait
        if len(self.requests) >= self.max_requests:
            sleep_time = self.window - (now - self.requests[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                # Recursive call to re-check
                await self.acquire()
        
        # Add current request
        self.requests.append(now)


class HardenedCompleteCSVProcessor:
    """Hardened processor with cost control, retries, and safety features"""
    
    def __init__(self, csv_path: str, batch_size: int = 25, budget_limit: float = 30.00):
        self.csv_path = csv_path
        self.batch_size = batch_size
        self.cost_tracker = CostTracker(budget_limit=budget_limit)
        self.rate_limiter = RateLimiter(max_requests=5, window_seconds=1.0)
        
        # Wrap research backend with our enhanced version
        self.research_backend = CompleteResearchBackend(
            search_context_size="high",
            max_urls_to_extract=10,
            include_fec_data=True
        )
        self.db = LocalDatabase()
        
        # Pause control
        self.pause_file = Path("PAUSE")
        self.progress_file = Path("processing_progress_hardened.json")
        
        # Tracking
        self.processed = 0
        self.failed = 0
        self.total_contacts = 0
        self.start_time = None
        
        # CSV column mapping (same as original)
        self.column_mapping = {
            'Contact ID': 'original_contact_id',
            'Full Name': 'full_name',
            'First Name': 'first_name', 
            'Last Name': 'last_name',
            'Email Address': 'email',
            'Opt-in Status': 'opt_in_status',
            'User Id': 'user_id',
            'Owner Id': 'owner_id',
            'Date Created': 'date_created',
            'Date Opt-in Status Changed': 'date_opt_in_status_changed',
            'Birthday': 'birthday',
            'Mobile Phone Number': 'mobile_phone_number',
            'Primary Phone Number': 'primary_phone_number',
            'Primary Phone Number Extension': 'primary_phone_number_extension',
            'Street Address 1': 'street_address_1',
            'Street Address 2': 'street_address_2',
            'City': 'city',
            'Postal/Zip': 'postal_zip',
            'Province/State/Region': 'province_state_region',
            'Country': 'country',
            'Time Zone': 'time_zone',
            'IP Address': 'ip_address',
            'Lead Source': 'lead_source',
            'Signup Page': 'signup_page',
            'Terms Agreement': 'terms_agreement',
            'Data Processing Consent': 'data_processing_consent',
            'Data Processing Consent Data': 'data_processing_consent_data',
            'Marketing Consent': 'marketing_consent',
            'Marketing Consent Date': 'marketing_consent_date',
            'Notes': 'notes',
            'Tags': 'tags',
            'UTM Campaign': 'utm_campaign',
            'UTM Content': 'utm_content',
            'UTM Medium': 'utm_medium',
            'UTM Term': 'utm_term',
            'UTM Source': 'utm_source',
            'Unsubscribe Date': 'unsubscribe_date',
            'Unsubscribe Reason': 'unsubscribe_reason',
            'Unsubscribe Feedback': 'unsubscribe_feedback',
            'Supporter Type': 'supporter_type',
            'Donation Type': 'donation_type',
            'Amount': 'amount',
            'phone status': 'phone_status',
            'email status': 'email_status',
            'calculated party': 'calculated_party',
            'support level': 'support_level',
            'County': 'county',
            'BPOU': 'bpou',
            'CD': 'cd',
            'Legislative': 'legislative',
            'SD': 'sd',
            'HD': 'hd',
            'Precinct': 'precinct',
            'Congress': 'congress',
            'State Senate': 'state_senate',
            'State House': 'state_house',
            'First Donation Date': 'first_donation_date',
            'Last Donation Date': 'last_donation_date',
            'Lifetime Given': 'lifetime_given',
            'Likely Age': 'likely_age',
            'Gender': 'gender',
            'School District': 'school_district',
            'Mayor': 'mayor',
            'City Council': 'city_council',
            'City Ward': 'city_ward'
        }
    
    def backup_database(self):
        """Create database backup before processing"""
        backup_name = f"campaign_local_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        try:
            shutil.copy2("campaign_local.db", backup_name)
            logger.info(f"✅ Database backed up to {backup_name}")
            return backup_name
        except Exception as e:
            logger.error(f"❌ Failed to backup database: {e}")
            raise
    
    def save_progress(self):
        """Save progress with enhanced tracking"""
        progress = {
            "current_index": self.processed + self.failed,
            "processed": self.processed,
            "failed": self.failed,
            "last_successful_contact": getattr(self, 'last_successful_contact', None),
            "cost_summary": self.cost_tracker.costs,
            "total_cost": self.cost_tracker.get_total(),
            "timestamp": datetime.now().isoformat()
        }
        with open(self.progress_file, 'w') as f:
            json.dump(progress, f, indent=2)
    
    def load_progress(self) -> Optional[Dict]:
        """Load saved progress"""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return None
    
    async def check_pause(self, current_index: int):
        """Check for pause request"""
        if self.pause_file.exists():
            self.save_progress()
            print("\n⏸️  PAUSE detected! Saving progress...")
            print(f"   Processed: {self.processed}, Failed: {self.failed}")
            print(f"   {self.cost_tracker.get_summary()}")
            print("   Delete PAUSE file to resume.")
            
            while self.pause_file.exists():
                await asyncio.sleep(5)
            
            print("▶️  Resuming processing...")
    
    def load_csv_contacts(self, skip_rows: int = 0, limit: Optional[int] = None) -> List[Dict]:
        """Load contacts from CSV with mapping"""
        contacts = []
        
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Skip rows if resuming
            for _ in range(skip_rows):
                next(reader, None)
            
            # Read contacts
            for i, row in enumerate(reader):
                if limit and i >= limit:
                    break
                
                # Map CSV columns to database columns
                contact = {}
                for csv_col, db_col in self.column_mapping.items():
                    contact[db_col] = row.get(csv_col, '')
                
                contact['row_number'] = skip_rows + i + 1
                contacts.append(contact)
        
        return contacts
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError))
    )
    async def process_contact_with_retry(self, contact: Dict) -> Dict:
        """Process contact with retry logic"""
        # Apply rate limiting
        await self.rate_limiter.acquire()
        
        # Track cost before processing
        try:
            self.cost_tracker.add_contact()
        except BudgetExceededError as e:
            logger.error(f"🛑 {e}")
            raise
        
        # Call the actual research backend
        name = contact['full_name']
        research_data = await self.research_backend.research_person(
            name=name,
            address=contact.get('street_address_1'),
            city=contact.get('city'),
            state=contact.get('province_state_region'),
            email=contact.get('email') if '@' in contact.get('email', '') else None,
            phone=contact.get('primary_phone_number')
        )
        
        return research_data
    
    async def process_contact(self, contact: Dict) -> bool:
        """Process a single contact with complete enrichment pipeline"""
        name = contact['full_name']
        if not name or name.strip() == '':
            logger.warning(f"Skipping contact with no name (row {contact['row_number']})")
            return False
        
        try:
            # Process with retry logic
            research_data = await self.process_contact_with_retry(contact)
            
            # Track successful contact
            self.last_successful_contact = {
                "name": name,
                "row": contact['row_number'],
                "id": contact.get('original_contact_id')
            }
            
            # Extract research results (same as original)
            urls = research_data.get('urls', [])
            linkedin_urls = research_data.get('linkedin_urls', [])
            urls_json = json.dumps(urls) if urls else None
            linkedin_urls_json = json.dumps(linkedin_urls) if linkedin_urls else None
            research_text = research_data.get('research_text', '')
            confidence = research_data.get('confidence', 'Medium')
            disambiguators = research_data.get('disambiguators', {})
            fec_data = research_data.get('fec_data', {})
            
            # Store disambiguators as JSON
            disambiguators_json = json.dumps(disambiguators) if disambiguators else None
            
            # Store FEC summary
            fec_summary = None
            if fec_data and fec_data.get('total_contributions', 0) > 0:
                fec_summary = json.dumps({
                    'total_amount': fec_data.get('total_amount', 0),
                    'contribution_count': fec_data.get('contribution_count', 0),
                    'party_leaning': fec_data.get('primary_party', 'Unknown'),
                    'years_active': fec_data.get('years_active', [])
                })
            
            # Prepare ALL data for insertion
            now = datetime.now().isoformat()
            
            # Build column names and values for ALL CSV columns plus enrichment
            columns = list(self.column_mapping.values()) + [
                'perplexity_urls', 'linkedin_urls', 'all_urls', 'raw_research', 'research_confidence',
                'research_status', 'researched_at', 'created_at', 'updated_at',
                'batch_id', 'source', 'disambiguators', 'fec_summary', 
                'perplexity_confidence', 'overall_confidence', 'content_extracted'
            ]
            
            values = []
            # Add all CSV column values with proper JSON handling
            for db_col in self.column_mapping.values():
                value = contact.get(db_col, '')
                # Apply same JSON handling as in database insert
                if value is not None:
                    if isinstance(value, (dict, list, tuple, set)):
                        if isinstance(value, list):
                            value = json.dumps(value) if value else "[]"
                        else:
                            value = json.dumps(value) if value else "{}"
                    elif isinstance(value, str) and len(value) > 50000:
                        value = value[:50000] + "... [truncated]"
                    elif not isinstance(value, (str, int, float, bool, type(None))):
                        value = str(value)
                values.append(value or '')
            
            # Validate all JSON fields before database insert
            def validate_json_field(json_str, field_name, default_value="{}"):
                """Validate JSON string and return safe default if invalid."""
                if json_str is None:
                    return None
                try:
                    # Test if JSON is valid by parsing it
                    json.loads(str(json_str))
                    return json_str
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Invalid JSON in {field_name}: {e}. Using default: {default_value}")
                    return default_value
            
            # Validate JSON fields
            urls_json = validate_json_field(urls_json, "urls_json", "[]")
            linkedin_urls_json = validate_json_field(linkedin_urls_json, "linkedin_urls_json", "[]")
            disambiguators_json = validate_json_field(disambiguators_json, "disambiguators_json", "{}")
            fec_summary = validate_json_field(fec_summary, "fec_summary", "{}")
            
            # Add enrichment values
            values.extend([
                urls_json,                # perplexity_urls
                linkedin_urls_json,       # linkedin_urls
                urls_json,                # all_urls (use same validated JSON)
                research_text[:10000] if research_text else None,  # raw_research
                confidence,               # research_confidence
                'completed',              # research_status
                now,                      # researched_at
                now,                      # created_at
                now,                      # updated_at
                f"csv_hardened_{datetime.now().strftime('%Y%m%d')}",  # batch_id
                'csv_import_hardened',    # source
                disambiguators_json,      # disambiguators
                fec_summary,              # fec_summary
                research_data.get('perplexity_confidence', 'Medium'),  # perplexity_confidence
                confidence,               # overall_confidence
                len(research_data.get('extracted_content', []))  # content_extracted
            ])
            
            # Final validation of ALL JSON values before insert
            logger.info(f"📝 Final validation before database insert for {name}")
            for i, (col, val) in enumerate(zip(columns, values)):
                if val and isinstance(val, str) and (col.endswith('_json') or col in ['disambiguators', 'fec_summary', 'perplexity_urls', 'linkedin_urls', 'all_urls']):
                    logger.info(f"🔍 Checking {col}: {str(val)[:100]}...")
                    try:
                        json.loads(val)
                        logger.info(f"✅ {col}: Valid JSON")
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"⚠️  {col}: Invalid JSON detected: {e}")
                        logger.warning(f"⚠️  Original value: {str(val)[:200]}...")
                        # Replace with safe default
                        if col.endswith('_json') or col in ['perplexity_urls', 'linkedin_urls', 'all_urls']:
                            values[i] = "[]"
                        else:
                            values[i] = "{}"
                        logger.warning(f"🔧 {col}: Replaced with safe default")
                
            # COMPREHENSIVE JSON validation for ALL fields that might contain JSON
            # This checks both generated fields AND CSV fields that contain JSON-like data
            potential_json_fields = ['notes', 'tags', 'data_processing_consent_data'] # Common CSV JSON fields
            
            for i, (col, val) in enumerate(zip(columns, values)):
                if val and isinstance(val, str):
                    # Check if field might contain JSON (starts with [ or { OR is a known JSON field)
                    is_json_like = (len(val) > 1 and (val.strip().startswith('[') or val.strip().startswith('{')))
                    is_known_json_field = col.lower() in potential_json_fields
                    
                    if is_json_like or is_known_json_field:
                        logger.info(f"🔍 Comprehensive check {col}: {str(val)[:100]}...")
                        try:
                            json.loads(val)
                            logger.info(f"✅ {col}: Valid JSON")
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(f"⚠️  {col}: Invalid JSON in CSV data: {e}")
                            logger.warning(f"⚠️  Original value: {str(val)[:200]}...")
                            # For CSV fields, escape the entire content as a JSON string
                            # This preserves the data but makes it SQLite-safe
                            values[i] = json.dumps(val)  # Escape the malformed JSON as a string
                            logger.warning(f"🔧 {col}: Escaped as JSON string")
                            
                    # Additional safety: Check for any string that contains unescaped quotes or backslashes
                    elif isinstance(val, str) and ('\\' in val or val.count('"') % 2 != 0):
                        logger.info(f"🔍 Quote/escape check {col}: {str(val)[:50]}...")
                        # Test if the string would be problematic as-is
                        try:
                            # Try to use it in a JSON context to see if it causes issues
                            test_json = json.dumps({"test": val})
                            json.loads(test_json)  # Validate the resulting JSON
                            logger.debug(f"✅ {col}: Safe for JSON context")
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(f"⚠️  {col}: Problematic string for JSON context: {e}")
                            # Clean up the string by escaping it properly
                            values[i] = json.dumps(val)[1:-1]  # Remove outer quotes, keep inner escaping
                            logger.warning(f"🔧 {col}: Cleaned string escaping")
            
            # Insert into database with ALL columns
            placeholders = ', '.join(['?' for _ in values])
            column_names = ', '.join(columns)
            
            # Debug: Log the exact INSERT statement
            logger.info(f"🎯 Attempting INSERT with {len(columns)} columns, {len(values)} values")
            logger.info(f"🎯 Column count check: {len(columns) == len(values)}")
            
            try:
                with self.db.get_connection() as conn:
                    cursor = conn.execute(f'''
                        INSERT INTO contacts ({column_names})
                        VALUES ({placeholders})
                    ''', values)
                    conn.commit()
            except sqlite3.OperationalError as e:
                if "malformed JSON" in str(e):
                    logger.error(f"🔍 SQLite JSON Error - this should not happen with comprehensive validation!")
                    logger.error(f"🔍 If you see this, there's still a JSON field we missed")
                    # Log a few sample values to help debug
                    for i, (col, val) in enumerate(zip(columns[:10], values[:10])):  # First 10 fields only
                        if val and isinstance(val, str) and len(val) > 10:
                            logger.error(f"Sample field {col}: {repr(str(val)[:100])}")
                    raise  # Re-raise the original error
                else:
                    raise  # Re-raise if it's not a JSON error
            
            # Log enrichment phases
            phases = research_data.get('search_phases', {})
            logger.info(f"✅ {name}: Complete enrichment")
            logger.info(f"   Phase 1 (Perplexity): {disambiguators.get('employer', 'N/A')} - {disambiguators.get('job_title', 'N/A')}")
            logger.info(f"   Phase 2 (SERP): Found {len(urls)} URLs, {len(linkedin_urls)} LinkedIn")
            logger.info(f"   Phase 3 (Content): Extracted from {phases.get('phase3_extraction', {}).get('urls_processed', 0)} URLs")
            logger.info(f"   Phase 4 (FEC): {phases.get('phase4_fec', {}).get('contributions_found', 0)} contributions")
            logger.info(f"   Overall confidence: {confidence}")
            
            return True
            
        except BudgetExceededError:
            # Re-raise budget errors to stop processing
            raise
            
        except Exception as e:
            logger.error(f"❌ Failed to process {name}: {e}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Even for failures, preserve original data
            try:
                now = datetime.now().isoformat()
                columns = list(self.column_mapping.values()) + [
                    'research_status', 'research_notes', 'created_at', 'updated_at',
                    'batch_id', 'source'
                ]
                
                values = []
                for db_col in self.column_mapping.values():
                    value = contact.get(db_col, '')
                    # Apply same JSON handling as in database insert
                    if value is not None:
                        if isinstance(value, (dict, list, tuple, set)):
                            if isinstance(value, list):
                                value = json.dumps(value) if value else "[]"
                            else:
                                value = json.dumps(value) if value else "{}"
                        elif isinstance(value, str) and len(value) > 50000:
                            value = value[:50000] + "... [truncated]"
                        elif not isinstance(value, (str, int, float, bool, type(None))):
                            value = str(value)
                    values.append(value or '')
                
                values.extend([
                    'failed',
                    str(e)[:500],
                    now,
                    now,
                    f"csv_hardened_{datetime.now().strftime('%Y%m%d')}",
                    'csv_import_hardened'
                ])
                
                # Validate JSON in error record too
                for i, (col, val) in enumerate(zip(columns, values)):
                    if val and isinstance(val, str) and (col.endswith('_json') or col in ['disambiguators', 'fec_summary', 'perplexity_urls', 'linkedin_urls', 'all_urls']):
                        try:
                            json.loads(val)
                        except (json.JSONDecodeError, TypeError):
                            values[i] = "[]" if col.endswith('_json') or col in ['perplexity_urls', 'linkedin_urls', 'all_urls'] else "{}"
                
                placeholders = ', '.join(['?' for _ in values])
                column_names = ', '.join(columns)
                
                with self.db.get_connection() as conn:
                    cursor = conn.execute(f'''
                        INSERT INTO contacts ({column_names})
                        VALUES ({placeholders})
                    ''', values)
                    conn.commit()
                    
            except Exception as db_error:
                logger.error(f"Failed to record error for {name}: {db_error}")
            
            return False
    
    async def process_csv(self, start_row: int = 0, end_row: Optional[int] = None):
        """Process CSV with complete enrichment pipeline and hardening"""
        self.start_time = datetime.now()
        
        print("🚀 HARDENED COMPLETE ENRICHMENT PIPELINE")
        print("=" * 60)
        print("📋 Pipeline phases:")
        print("   1. Perplexity disambiguation (employer, title, education)")
        print("   2. Bright Data SERP (find all URLs)")
        print("   3. Content extraction (blogs, news, company pages)")
        print("   4. FEC political contributions")
        print("   5. LinkedIn URLs collected for later processing")
        print("=" * 60)
        print("🛡️  HARDENING FEATURES:")
        print(f"   💰 Cost tracking with ${self.cost_tracker.budget_limit:.2f} budget limit")
        print("   🔄 Retry logic for API failures (3 attempts)")
        print("   ⏱️  Enhanced rate limiting (5 req/sec)")
        print("   💾 Database backup before processing")
        print("   📊 Enhanced progress tracking")
        print("=" * 60)
        print("⏸️  TO PAUSE: Create a file named 'PAUSE' in this directory")
        print("▶️  TO RESUME: Delete the PAUSE file")
        print("=" * 60)
        
        # Create database backup
        try:
            backup_file = self.backup_database()
        except Exception as e:
            print(f"❌ Failed to create backup: {e}")
            if input("Continue without backup? (y/n): ").lower() != 'y':
                return
        
        # Check for saved progress
        saved_progress = self.load_progress()
        if saved_progress and start_row == 0:
            print(f"\n📂 Found saved progress from {saved_progress['timestamp']}")
            print(f"   Processed: {saved_progress['processed']}, Failed: {saved_progress['failed']}")
            print(f"   Total cost so far: ${saved_progress['total_cost']:.2f}")
            if saved_progress.get('last_successful_contact'):
                print(f"   Last contact: {saved_progress['last_successful_contact']['name']}")
            resume = input("Resume from saved progress? (y/n): ").lower().strip()
            if resume == 'y':
                start_row = saved_progress['current_index']
                self.processed = saved_progress['processed']
                self.failed = saved_progress['failed']
                # Restore cost tracker
                if 'cost_summary' in saved_progress:
                    self.cost_tracker.costs = saved_progress['cost_summary']
                print(f"▶️  Resuming from contact {start_row + 1}")
        
        # Load contacts
        limit = (end_row - start_row) if end_row else None
        contacts = self.load_csv_contacts(skip_rows=start_row, limit=limit)
        self.total_contacts = len(contacts) + start_row
        
        if not contacts:
            print("❌ No contacts to process")
            return
        
        print(f"\n🔬 Starting processing of {len(contacts)} contacts...")
        print(f"📊 Complete enrichment with all data sources")
        print(f"⏱️  Estimated time: {len(contacts) * 3 / 60:.1f} minutes")
        print(f"💰 Estimated cost: ${len(contacts) * 0.02:.2f}")
        
        try:
            # Process contacts one by one
            for i, contact in enumerate(contacts):
                # Check for pause request
                await self.check_pause(start_row + i)
                
                # Process the contact
                success = await self.process_contact(contact)
                if success:
                    self.processed += 1
                else:
                    self.failed += 1
                
                # Progress update
                current_total = self.processed + self.failed
                progress = current_total / self.total_contacts * 100
                elapsed = (datetime.now() - self.start_time).total_seconds() / 60
                
                # Update every 5 contacts
                if current_total % 5 == 0:
                    remaining = (self.total_contacts - current_total) * (elapsed / current_total)
                    print(f"\n📊 Progress: {current_total}/{self.total_contacts} ({progress:.1f}%)")
                    print(f"   ✅ Processed: {self.processed}, ❌ Failed: {self.failed}")
                    print(f"   ⏱️  Elapsed: {elapsed:.1f}m, Remaining: {remaining:.1f}m")
                    print(f"   {self.cost_tracker.get_summary()}")
                    
                    # Save progress periodically
                    self.save_progress()
        
        except BudgetExceededError as e:
            print(f"\n🛑 STOPPING: {e}")
            print(f"   Processed {self.processed} contacts before hitting budget limit")
            self.save_progress()
        
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted! Saving progress...")
            self.save_progress()
            raise
        
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            self.save_progress()
            raise
        
        finally:
            # Final summary
            total_time = (datetime.now() - self.start_time).total_seconds() / 60
            print("\n" + "=" * 60)
            print("📊 FINAL SUMMARY")
            print("=" * 60)
            print(f"✅ Successfully processed: {self.processed}")
            print(f"❌ Failed: {self.failed}")
            print(f"⏱️  Total time: {total_time:.1f} minutes")
            print(f"{self.cost_tracker.get_summary()}")
            print(f"💾 Database backup: {backup_file if 'backup_file' in locals() else 'Not created'}")
            
            # Check database state
            with self.db.get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM contacts")
                total_in_db = cursor.fetchone()[0]
                print(f"📊 Total contacts in database: {total_in_db}")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Process CSV with hardened complete enrichment pipeline')
    parser.add_argument('--csv', default='Input/SD42_SD45_filtered.csv', help='CSV file path')
    parser.add_argument('--start', type=int, default=0, help='Start row (0-based)')
    parser.add_argument('--end', type=int, help='End row (exclusive)')
    parser.add_argument('--budget', type=float, default=30.00, help='Budget limit in USD')
    
    args = parser.parse_args()
    
    # Verify CSV exists
    if not os.path.exists(args.csv):
        print(f"❌ CSV file not found: {args.csv}")
        sys.exit(1)
    
    # Check for required environment variables
    required_vars = ['PERPLEXITY_API_KEY', 'BRIGHT_DATA_API_KEY']
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        print("   Please set them in your .env file")
        sys.exit(1)
    
    # Create processor and run
    processor = HardenedCompleteCSVProcessor(
        csv_path=args.csv,
        budget_limit=args.budget
    )
    
    await processor.process_csv(start_row=args.start, end_row=args.end)


if __name__ == "__main__":
    asyncio.run(main())