## FEATURE:

Build a fully automated, secure, and cost-efficient system that:
- Reads contact information from a CSV file (name, email, company)
- Performs web research on each individual using WebSailor
- Enriches data with structured JSON tags for microtargeting using AI (GPT-4o/Claude)
- Stores enriched data in PostgreSQL with JSONB for flexible querying
- Provides a secure Google Sheets interface for customers
- Keeps research methods and tagging logic completely private

### Core Components:
1. **CSV Ingestion**: Process contacts from CSV files
2. **Orchestration**: Self-hosted n8n workflow automation
3. **Research Agent**: WebSailor for gathering web information
4. **AI Tagging**: Structured data extraction into JSONB format
5. **Database**: Google Cloud SQL PostgreSQL with security abstraction
6. **Frontend**: Google Sheets with automated sync
7. **Microtargeting**: Internal query system for audience segmentation

## EXAMPLES:

Create the following example structure in `examples/`:
- `examples/csv_sample.csv` - Sample input CSV with name, email, company
- `examples/json_schema.json` - Complete JSONB schema for structured tags
- `examples/n8n_workflow.json` - Example n8n workflow configuration
- `examples/database_schema.sql` - PostgreSQL table and view definitions
- `examples/query_examples.sql` - Sample JSONB queries for microtargeting
- `examples/apps_script.js` - Google Apps Script for data sync

## DOCUMENTATION:

- n8n Documentation: https://docs.n8n.io/
- WebSailor API Documentation: [Add WebSailor docs URL]
- PostgreSQL JSONB: https://www.postgresql.org/docs/current/datatype-json.html
- Google Apps Script JDBC: https://developers.google.com/apps-script/guides/jdbc
- Google Cloud SQL: https://cloud.google.com/sql/docs/postgres

## OTHER CONSIDERATIONS:

### Security Requirements:
- Database views to hide proprietary tags and raw research data
- Read-only Google Sheets access for customers
- Secure credential management for all API keys
- Private hosting for n8n instance

### Technical Requirements:
- Use python-dotenv for environment variables
- Implement retry logic for web research failures
- Handle rate limiting for external APIs
- Validate JSON structure before database insertion
- Implement proper error logging and monitoring

### Data Structure Requirements:
- Standardized JSONB schema for all contacts
- Include metadata (timestamps, sources)
- Support for nested attributes (skills, interests, roles)
- Maintain data consistency across updates

### Performance Considerations:
- Process contacts in batches to avoid timeouts
- Implement database indexing on JSONB fields
- Cache frequently accessed data
- Optimize Google Sheets sync for large datasets

### Deliverables:
- Complete n8n workflow configuration
- Database setup scripts with security views
- Google Apps Script for automated sync
- Documentation for setup and maintenance
- Example queries for common microtargeting scenarios
- .env.example with all required variables