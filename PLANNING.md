## Project Planning: Campaign Microtargeting System

## 1. Project Overview & Goals

This project aims to build a robust, automated system for **campaign microtargeting** by enriching contact data with comprehensive, nuanced information from various online sources. It will:
- Ingest contact information from a CSV file (First Name, Last Name, Email, Phone, Address).
- Perform comprehensive web research to enrich contact data with specific signals relevant to campaign segmentation.
- Utilize AI for structured data extraction and nuanced tagging for microtargeting.
- Store enriched data in PostgreSQL with JSONB for flexible querying.
- Provide a secure Google Sheets interface for customers.
- Maintain privacy of research methods and tagging logic.

## 2. Core Pipeline Architecture: Detailed Tech Stack

The system is designed as a multi-component, intelligence-driven pipeline to ensure high accuracy and efficiency in data enrichment.

### Component 1: Identity Resolution

*   **Strategy:** To establish a high-confidence "Identity Anchor" by triangulating the individual's identity using their name and physical address. This is the critical first step to ensure all subsequent research is conducted on the correct person, especially for common names.
*   **Tools:** A **People Data API** (specific provider to be selected after further research).
*   **Rationale:** Dedicated People Data APIs are designed to perform reverse address lookups and provide demographic data (like age) which is crucial for disambiguation.
*   **Implementation Details:** The n8n workflow will make an API call using the provided `Full Name`, `Street Address`, `City`, `State`, and `Zip`.
*   **Pros:** Provides a reliable `age` and confirms the individual's presence at the given address, significantly reducing ambiguity.
*   **Cons/Challenges:** Requires integration with a third-party API, which will incur costs.

### Component 2: Web Discovery & Search (SERP)

*   **Strategy:** To perform broad web searches to identify the top 10-15 most relevant public web pages (URLs) for each individual. This component acts as our primary "dossier builder."
*   **Tools:**
    *   **Perplexity.ai** (as the search engine).
    *   **Nanobrowser** (as the Chrome MCP for browser automation).
*   **Rationale:**
    *   **Perplexity.ai:** Chosen for its ability to synthesize information and potentially provide more relevant results than traditional search engines for complex queries. Your successful test demonstrated its capability to return structured JSON output when prompted correctly.
    *   **Nanobrowser (Chrome MCP):** Proposed as the mechanism to interact with Perplexity.ai. It's an open-source Chrome extension that allows AI agents to control the browser, leveraging existing browser configurations and login states. This is intended to bypass traditional API costs for SERP.
*   **Implementation Details:**
    *   The n8n workflow would need to orchestrate Nanobrowser to:
        1.  Open Perplexity.ai.
        2.  Input a highly specific prompt into the search bar.
        3.  Wait for the search results.
        4.  Locate and click the "Copy" button for the Markdown output.
        5.  Extract the JSON object from the copied text.
    *   **Perplexity Prompt (Example):**
        ```
        Find and list the top 10-15 most relevant public web pages for the individual named "[Full Name]" who resides at "[Street Address 1], [City], [State]".

        **Crucial Disambiguation Instruction:** It is common for multiple individuals with the same name to reside in the same city. Therefore, it is absolutely critical to focus on identifying the *correct* person. If multiple individuals with the same name appear in search results, use the provided address, and if available, email address ([Email Address]) or phone number ([Phone Number]) to accurately disambiguate and identify the specific individual. Prioritize results that strongly correlate with these identifying details.

        Focus your search on identifying pages that reveal:
        - Professional profiles (e.g., LinkedIn, personal websites, company bios)
        - News articles or press releases directly mentioning them
        - Public records related to their professional or financial activities
        - Social media profiles (X.com, Facebook, personal blogs)
        - Any mentions of board positions, speaking engagements, publications, investments, or charitable involvement.

        **URL Quality & Relevance:** Prioritize pages that are *directly about* this specific individual or contain substantial, relevant information. Do not include generic directory listings, irrelevant search results, or duplicate URLs pointing to the exact same content.

        Return the response as a JSON object with the following keys:
        - **"urls"**: An array of strings, where each string is a unique, relevant URL.
        - **"confidence_score"**: A string indicating your confidence in the disambiguation and relevance of the URLs. Use "High" if you are very certain, "Medium" if there was some ambiguity but you made the best choice, or "Low" if the results were highly ambiguous or insufficient.
        - **"notes"**: An optional string for any important observations, such as remaining ambiguity, difficulty finding relevant information, or specific challenges encountered during the search.

        Example JSON format:
        {
          "urls": [
            "https://example.com/profile1",
            "https://example.org/article2"
          ],
          "confidence_score": "High",
          "notes": "Found clear LinkedIn profile and recent news article."
        }
        ```
*   **Pros:**
    *   **Cost-Effective:** Leverages Perplexity's free access and self-hosted browser automation, aiming for $0 direct cost for SERP.
    *   **Intelligent Search:** Perplexity's LLM-driven search can potentially provide more nuanced and relevant results for complex queries.
    *   **Structured Output:** The prompt is designed to yield JSON, simplifying parsing.
*   **Cons/Challenges:**
    *   **Scalability:** This is the primary concern. Browser automation (even with an MCP) is inherently resource-intensive and slow for high-volume, unattended batch processing. Running multiple browser instances simultaneously for thousands of contacts will be a significant bottleneck and resource drain.
    *   **Reliability/Brittleness:** Browser UIs can change, breaking automation scripts. While Nanobrowser uses AI, managing these failures across a large batch in an unattended environment is complex.
    *   **Terms of Service (ToS):** Automated, high-volume querying of Perplexity.ai will likely violate its ToS and lead to rate limits, CAPTCHAs, or account suspensions.
    *   **Anti-Blocking:** Unlike dedicated SERP APIs, this setup does not inherently manage proxies or advanced anti-blocking techniques, making it vulnerable to detection.

### Component 3: Content Extraction

*   **Strategy:** To convert raw HTML content from the discovered URLs into clean, LLM-friendly Markdown, removing boilerplate and noise.
*   **Tools:**
    *   **Mozilla Readability** (npm package).
    *   **ReaderLM-v2** (a 1.5B parameter model, self-hosted).
*   **Rationale:** This combination provides a highly cost-effective and efficient solution for preparing web content for AI analysis. Mozilla Readability handles initial HTML cleaning, and ReaderLM-v2 further refines it into clean Markdown, avoiding per-request API costs.
*   **Implementation Details:**
    *   The n8n workflow will fetch the raw HTML of each URL from the dossier.
    *   Mozilla Readability will be used as a pre-processing step to extract the main content from the HTML.
    *   The cleaned HTML will then be sent to a self-hosted `ReaderLM-v2` endpoint.
    *   `ReaderLM-v2` will convert the HTML into clean Markdown.
*   **Infrastructure Requirements:** A GPU with 8GB+ VRAM (or 4GB with quantization) is required to run `ReaderLM-v2` locally.
*   **Pros:**
    *   **Cost-Efficient:** $0 direct cost (leveraging existing GPU infrastructure).
    *   **LLM-Ready Output:** Produces clean Markdown, ideal for input into GPT-4o.
    *   **Control:** Full control over the model and processing.
*   **Cons/Challenges:** Requires managing and maintaining a self-hosted AI model and dedicated GPU resources.

### Component 4: Specialized Data

*   **Strategy:** To gather specific, high-value data points from sources that require targeted queries or specialized scraping.
*   **Tools:**
    *   **Bright Data API for LinkedIn:** For structured professional profile data.
    *   **FEC API:** Direct queries to `fec.gov` for political contribution records.
    *   **Direct HTTP Requests:** For checking email domain websites.
    *   **X.com / Facebook:** **No dedicated scraping.** We will rely on public X.com/Facebook pages appearing in the general SERP results (processed by Perplexity/Nanobrowser) and then extracted by `ReaderLM-v2`.
*   **Rationale:** These sources provide unique, critical data for microtargeting. Using specialized APIs (like Bright Data for LinkedIn) is more reliable and efficient than general scraping. Direct API calls to public databases (like FEC) are cost-effective. Avoiding dedicated social media scraping mitigates ToS risks and high costs.
*   **Pros:** Access to highly relevant, structured data. Cost-effective for FEC and domain checks.
*   **Cons/Challenges:** Bright Data LinkedIn API incurs costs. Social media scraping remains a significant challenge due to ToS and technical complexity.

### Component 5: AI Synthesis

*   **Strategy:** To analyze all collected and cleaned data, synthesize it, and generate nuanced insights and structured JSON tags for microtargeting.
*   **Tools:** **GPT-4o** (via API).
*   **Rationale:** GPT-4o's advanced reasoning capabilities are essential for inferring complex attributes like political leanings, key issues, financial capacity, and lifestyle indicators from diverse, often unstructured, data.
*   **Implementation Details:** The n8n workflow will compile all collected data (Identity Anchor, clean Markdown content, structured data from specialized sources) into a comprehensive prompt for GPT-4o. The prompt will instruct GPT-4o to act as a campaign research analyst and populate a predefined JSON schema.
*   **Pros:** High-quality, nuanced analysis and structured output.
*   **Cons/Challenges:** Incurs per-token costs. Requires careful prompt engineering to ensure accurate and consistent output.

## 3. Infrastructure Requirements

*   **n8n Instance:** The central orchestration engine for the entire workflow.
*   **ReaderLM-v2 Server:** A dedicated server with a GPU (8GB+ VRAM recommended) for self-hosting the `ReaderLM-v2` model.
*   **PostgreSQL Database:** For storing the final enriched contact data in a structured format (including JSONB fields).
*   **Chrome Browser with Nanobrowser Extension:** For the Perplexity.ai interaction (requires a system capable of running multiple browser instances if parallel processing is attempted).

## 4. Data Inputs

The system will receive contact information with the following fields:
- `Full Name`
- `First Name`
- `Last Name`
- `Email Address`
- `Mobile Phone Number`
- `Primary Phone Number`
- `Primary Phone Number Extension`
- `Street Address 1`
- `Street Address 2`
- `City`
- `Postal/Zip`
- `Province/State/Region`

## 5. Deliverables

- Complete n8n workflow configuration.
- Database setup scripts with security views.
- Google Apps Script for automated sync.
- Documentation for setup and maintenance.
- Example queries for common microtargeting scenarios.
- `.env.example` with all required variables.

## 6. Conventions & Standards

(Refer to `CLAUDE.md` for detailed coding, testing, and documentation conventions.)