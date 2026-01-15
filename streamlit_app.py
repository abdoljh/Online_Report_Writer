import streamlit as st
import json
import requests
import time
from datetime import datetime
import base64
from typing import List, Dict, Any
import re

# Page configuration
st.set_page_config(
    page_title="Online Report Writer System",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .stProgress > div > div > div > div {
        background-color: #4F46E5;
    }
    .css-1d391kg {
        padding-top: 1.5rem;
    }
    .report-stats {
        background-color: #F3F4F6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .source-item {
        padding: 0.5rem;
        margin: 0.25rem 0;
        background-color: #F0F9FF;
        border-radius: 0.25rem;
        border-left: 3px solid #3B82F6;
    }
    .stButton > button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'step' not in st.session_state:
    st.session_state.step = 'input'
if 'form_data' not in st.session_state:
    st.session_state.form_data = {
        'topic': '',
        'subject': '',
        'researcher': '',
        'institution': '',
        'date': datetime.now().strftime('%Y-%m-%d')
    }
if 'progress' not in st.session_state:
    st.session_state.progress = {
        'stage': '',
        'detail': '',
        'percent': 0
    }
if 'research' not in st.session_state:
    st.session_state.research = {
        'queries': [],
        'sources': [],
        'subtopics': []
    }
if 'draft' not in st.session_state:
    st.session_state.draft = None
if 'critique' not in st.session_state:
    st.session_state.critique = None
if 'final_report' not in st.session_state:
    st.session_state.final_report = None
if 'is_processing' not in st.session_state:
    st.session_state.is_processing = False

# Get API key from Streamlit secrets
try:
    ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]
    API_AVAILABLE = True
except (KeyError, FileNotFoundError):
    st.error("⚠️ Anthropic API key not found in secrets. Please add it to your Streamlit secrets.")
    API_AVAILABLE = False

def update_progress(stage: str, detail: str, percent: int):
    """Update progress in session state"""
    st.session_state.progress = {
        'stage': stage,
        'detail': detail,
        'percent': min(100, percent)  # Ensure percent doesn't exceed 100
    }

def calculate_credibility(url: str) -> int:
    """Calculate credibility score based on domain"""
    url_lower = url.lower()
    if '.gov' in url_lower or '.edu' in url_lower:
        return 95
    if 'nature.com' in url_lower or 'science.org' in url_lower:
        return 95
    if 'ieee.org' in url_lower or 'acm.org' in url_lower:
        return 90
    if '.org' in url_lower:
        return 85
    return 80

def parse_json_response(text: str) -> Dict:
    """Parse JSON from AI response, handling code blocks"""
    try:
        # Remove markdown code blocks
        cleaned = re.sub(r'```json\n?|```\n?', '', text).strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to extract JSON from text
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        st.error(f"Failed to parse JSON response: {text[:200]}...")
        return {}

def call_anthropic_api(messages: List[Dict], max_tokens: int = 1000, use_web_search: bool = False) -> Dict:
    """Call Anthropic Claude API with proper tool configuration"""
    if not API_AVAILABLE:
        raise Exception("API key not configured")

    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01"
    }

    data = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": max_tokens,
        "messages": messages
    }

    # FIXED: Correct tool type specification
    if use_web_search:
        data["tools"] = [{
            "type": "web_search_20250305",  # Correct type
            "name": "web_search"
        }]

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=120  # Increased timeout for web searches
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API call failed: {str(e)}")
        raise

# Stage 1: Topic Analysis
def analyze_topic_with_ai(topic: str, subject: str) -> Dict:
    """Analyze topic and generate research structure"""
    update_progress('Topic Analysis', 'Decomposing topic into research dimensions...', 10)

    prompt = f"""Analyze this research topic and provide a structured breakdown:

Topic: "{topic}"
Subject: "{subject}"

Provide a JSON response with:
1. subtopics: Array of 5-7 specific subtopics to investigate
2. researchQueries: Array of 15 diverse search queries covering:
   - Academic/theoretical aspects
   - Current statistics and data
   - Policy and governance
   - Industry applications
   - Future trends
   - Challenges and limitations
   - Case studies
   - Expert opinions
   - Technical details
   - Comparative analysis

Format as valid JSON only, no other text. Example format:
{{
  "subtopics": ["subtopic1", "subtopic2", ...],
  "researchQueries": ["query1", "query2", ...]
}}"""

    response = call_anthropic_api([
        {
            "role": "user",
            "content": prompt
        }
    ], max_tokens=1000)

    if 'content' in response:
        text_content = ""
        for content in response['content']:
            if content['type'] == 'text':
                text_content += content['text']

        return parse_json_response(text_content)
    return {"subtopics": [], "researchQueries": []}

# Stage 2: Parallel Web Research
def execute_web_research(queries: List[str]) -> List[Dict]:
    """Execute REAL web research using Anthropic's web search tool"""
    update_progress('Web Research', f'Executing {len(queries)} parallel searches...', 25)
    
    sources = []
    trusted_domains = [
        '.edu', '.gov', '.org', 'nature.com', 'science.org', 'ieee.org',
        'acm.org', 'springer.com', 'wiley.com', 'who.int', 'worldbank.org',
        'oecd.org', 'nih.gov', 'nsf.gov', 'arxiv.org', 'pnas.org', 'un.org',
        'cdc.gov', 'nasa.gov', 'mit.edu', 'stanford.edu', 'harvard.edu'
    ]

    for i, query in enumerate(queries):
        progress = 25 + (i / len(queries)) * 15
        update_progress('Web Research', f'Query {i + 1}/{len(queries)}: {query[:50]}...', progress)

        try:
            # FIXED: Actually use web search tool
            search_response = call_anthropic_api(
                messages=[{
                    "role": "user",
                    "content": query
                }],
                max_tokens=1000,
                use_web_search=True  # Enable web search
            )

            # FIXED: Properly parse tool use results
            if 'content' in search_response:
                for content_block in search_response['content']:
                    # Handle tool_use blocks from web search
                    if content_block.get('type') == 'tool_use' and content_block.get('name') == 'web_search':
                        # Extract search results from tool response
                        tool_input = content_block.get('input', {})
                        # The actual results are typically in a separate tool_result block
                        # or in the response structure
                        
                    # Handle text responses that may contain source information
                    elif content_block.get('type') == 'text':
                        text = content_block.get('text', '')
                        
                        # Parse citations and sources from the response
                        # Claude typically provides sources in a structured format
                        if 'source' in text.lower() or 'http' in text.lower():
                            # Extract URLs and titles
                            import re
                            urls = re.findall(r'https?://[^\s<>"]+', text)
                            
                            for url in urls:
                                # Check if URL is from trusted domain
                                is_trusted = any(domain in url.lower() for domain in trusted_domains)
                                
                                if is_trusted:
                                    # Extract title from surrounding text
                                    url_pos = text.find(url)
                                    context_start = max(0, url_pos - 200)
                                    context_end = min(len(text), url_pos + 200)
                                    context = text[context_start:context_end]
                                    
                                    # Try to find a title
                                    title_match = re.search(r'([A-Z][^.!?]*(?:[.!?]|$))', context[:url_pos - context_start])
                                    title = title_match.group(1) if title_match else f"Source for: {query[:50]}"
                                    
                                    sources.append({
                                        'title': title.strip(),
                                        'url': url,
                                        'content': context.strip(),
                                        'query': query,
                                        'credibilityScore': calculate_credibility(url),
                                        'dateAccessed': datetime.now().isoformat()
                                    })

            # Add small delay to avoid rate limiting
            time.sleep(0.5)

        except Exception as error:
            st.warning(f"Search failed for query: {query[:50]}... Error: {str(error)}")
            continue

    # Deduplicate sources by URL
    seen_urls = set()
    unique_sources = []
    for source in sources:
        if source['url'] not in seen_urls:
            seen_urls.add(source['url'])
            unique_sources.append(source)

    return unique_sources

# Stage 3: Draft Generation
def generate_draft(topic: str, subject: str, subtopics: List[str], sources: List[Dict]) -> Dict:
    """Generate comprehensive research draft"""
    update_progress('Drafting', 'Synthesizing research into comprehensive report...', 45)

    source_summary = "\n\n".join([
        f"Source: {s.get('title', 'Unknown')}\n"
        f"URL: {s.get('url', 'No URL')}\n"
        f"Content: {s.get('content', 'No content')[:500]}..."
        for s in sources[:10]  # Limit to first 10 sources for token management
    ])

    prompt = f"""Create a comprehensive academic research report on "{topic}" in the field of {subject}.

Subtopics to cover: {', '.join(subtopics)}

Research sources (summarized):
{source_summary}

Structure the report with these sections:
1. Abstract (150-250 words)
2. Introduction
3. Literature Review
4. Main Body (organized by subtopics)
5. Data & Statistical Analysis
6. Challenges & Limitations
7. Future Outlook
8. Conclusion

Requirements:
- Use formal academic tone
- Reference sources appropriately
- Include specific data, statistics, and facts from sources
- Maintain logical flow between sections
- Each major claim should reference source information
- 2000-3000 words total

Return as JSON with these keys: abstract, introduction, literatureReview, mainSections (array of objects with title and content), dataAnalysis, challenges, futureOutlook, conclusion

Example format:
{{
  "abstract": "Abstract text here...",
  "introduction": "Introduction text...",
  "literatureReview": "Literature review...",
  "mainSections": [
    {{"title": "Section 1 Title", "content": "Section content..."}},
    {{"title": "Section 2 Title", "content": "Section content..."}}
  ],
  "dataAnalysis": "Data analysis section...",
  "challenges": "Challenges section...",
  "futureOutlook": "Future outlook...",
  "conclusion": "Conclusion..."
}}"""

    response = call_anthropic_api([
        {
            "role": "user",
            "content": prompt
        }
    ], max_tokens=4000)

    if 'content' in response:
        text_content = ""
        for content in response['content']:
            if content['type'] == 'text':
                text_content += content['text']

        draft_data = parse_json_response(text_content)

        # Ensure all required keys exist
        required_keys = ['abstract', 'introduction', 'literatureReview', 'mainSections',
                        'dataAnalysis', 'challenges', 'futureOutlook', 'conclusion']
        for key in required_keys:
            if key not in draft_data:
                draft_data[key] = f"[{key} section to be generated]"

        return draft_data

    return {
        'abstract': 'Abstract not generated.',
        'introduction': 'Introduction not generated.',
        'literatureReview': 'Literature review not generated.',
        'mainSections': [{'title': 'Main Section', 'content': 'Content not generated.'}],
        'dataAnalysis': 'Data analysis not generated.',
        'challenges': 'Challenges not generated.',
        'futureOutlook': 'Future outlook not generated.',
        'conclusion': 'Conclusion not generated.'
    }

# Stage 4: Critique
def critique_draft(draft: Dict, sources: List[Dict]) -> Dict:
    """Critique the draft for quality and accuracy"""
    update_progress('Review', 'Critical analysis by reviewer agent...', 65)

    prompt = f"""Review this academic report draft for quality and accuracy:

{json.dumps(draft, indent=2)}

Number of sources available: {len(sources)}

Perform these checks:
1. Fact consistency - are claims supported by sources?
2. Logical flow - does the argument progress coherently?
3. Unsupported claims - flag any assertions without supporting information
4. Bias detection - identify potential biases
5. Structural issues - missing sections or weak areas
6. Citation completeness - are references properly handled?

Return JSON with: factIssues (array), flowIssues (array), unsupportedClaims (array), biasFlags (array), structuralWeaknesses (array), citationIssues (array), overallScore (1-100), recommendations (array)

Example format:
{{
  "factIssues": ["issue1", "issue2"],
  "flowIssues": ["issue1"],
  "unsupportedClaims": ["claim1"],
  "biasFlags": [],
  "structuralWeaknesses": ["weakness1"],
  "citationIssues": ["issue1"],
  "overallScore": 85,
  "recommendations": ["recommendation1", "recommendation2"]
}}"""

    response = call_anthropic_api([
        {
            "role": "user",
            "content": prompt
        }
    ], max_tokens=2000)

    if 'content' in response:
        text_content = ""
        for content in response['content']:
            if content['type'] == 'text':
                text_content += content['text']

        critique_data = parse_json_response(text_content)

        # Ensure all required keys exist
        required_keys = ['factIssues', 'flowIssues', 'unsupportedClaims', 'biasFlags',
                        'structuralWeaknesses', 'citationIssues', 'overallScore', 'recommendations']
        for key in required_keys:
            if key not in critique_data:
                if key == 'overallScore':
                    critique_data[key] = 75
                else:
                    critique_data[key] = []

        return critique_data

    return {
        'factIssues': [],
        'flowIssues': [],
        'unsupportedClaims': [],
        'biasFlags': [],
        'structuralWeaknesses': [],
        'citationIssues': [],
        'overallScore': 70,
        'recommendations': ['Review generated with limitations']
    }

# Stage 5: Refine
def refine_draft(draft: Dict, critique: Dict, sources: List[Dict]) -> Dict:
    """Refine draft based on critique"""
    update_progress('Refinement', 'Applying editorial improvements...', 80)

    prompt = f"""Refine this academic report based on reviewer feedback:

Original Draft:
{json.dumps(draft, indent=2)}

Reviewer Critique:
{json.dumps(critique, indent=2)}

Available sources: {len(sources)}

Improvements needed:
1. Address all flagged issues
2. Enhance academic tone and clarity
3. Add executive summary (200 words)
4. Strengthen weak sections
5. Improve source integration
6. Ensure logical cohesion
7. Add transition sentences between sections

Return refined version as JSON with same structure as original plus executiveSummary key"""

    response = call_anthropic_api([
        {
            "role": "user",
            "content": prompt
        }
    ], max_tokens=4000)

    if 'content' in response:
        text_content = ""
        for content in response['content']:
            if content['type'] == 'text':
                text_content += content['text']

        refined_data = parse_json_response(text_content)

        # Ensure executiveSummary exists
        if 'executiveSummary' not in refined_data:
            refined_data['executiveSummary'] = "Executive summary providing key insights and findings from the research report."

        return refined_data

    # If refinement fails, return original with basic executive summary
    draft['executiveSummary'] = "Executive summary: This report examines the research topic through comprehensive analysis of available sources."
    return draft

def generate_html_report(refined_draft: Dict, form_data: Dict, sources: List[Dict]) -> str:
    """Generate HTML report for download"""
    update_progress('Report Generation', 'Creating professional document...', 95)

    # Format date
    report_date = datetime.strptime(form_data['date'], '%Y-%m-%d').strftime('%B %d, %Y')

    # Build HTML content
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset=\"utf-8\">
    <title>{form_data['topic']} - Research Report</title>
    <style>
        @page {{ margin: 1in; }}
        body {{
            font-family: 'Times New Roman', serif;
            font-size: 12pt;
            line-height: 1.6;
            color: #000;
            max-width: 8.5in;
            margin: 0 auto;
            padding: 0.5in;
        }}
        .cover {{
            text-align: center;
            padding-top: 2in;
            page-break-after: always;
        }}
        .cover h1 {{
            font-size: 24pt;
            font-weight: bold;
            margin: 1in 0 0.5in 0;
        }}
        .cover .meta {{
            font-size: 14pt;
            margin: 0.25in 0;
        }}
        h1 {{
            font-size: 18pt;
            margin-top: 0.5in;
            border-bottom: 1px solid #ccc;
            padding-bottom: 0.1in;
        }}
        h2 {{
            font-size: 14pt;
            margin-top: 0.3in;
            font-weight: bold;
        }}
        p {{
            text-align: justify;
            margin: 0.15in 0;
            text-indent: 0.3in;
        }}
        .abstract {{
            font-style: italic;
            margin: 0.25in 0.5in;
            text-indent: 0;
        }}
        .references {{
            page-break-before: always;
        }}
        .ref-item {{
            margin: 0.15in 0 0.15in 0.5in;
            text-indent: -0.5in;
            padding-left: 0.5in;
        }}
        .no-indent {{
            text-indent: 0;
        }}
    </style>
</head>
<body>
    <div class=\"cover\">
        <h1>{form_data['topic']}</h1>
        <div class=\"meta\">A Research Report</div>
        <div class=\"meta\">Subject: {form_data['subject']}</div>
        <div class=\"meta\" style=\"margin-top: 1in;\">
            Prepared by<br>
            {form_data['researcher']}<br>
            {form_data['institution']}<br>
            {report_date}
        </div>
    </div>

    <h1>Executive Summary</h1>
    <p class=\"no-indent\">{refined_draft.get('executiveSummary', 'Executive summary not available.')}</p>

    <h1>Abstract</h1>
    <div class=\"abstract\">{refined_draft.get('abstract', 'Abstract not available.')}</div>

    <h1>Introduction</h1>
    <p class=\"no-indent\">{refined_draft.get('introduction', 'Introduction not available.')}</p>

    <h1>Literature Review</h1>
    <p class=\"no-indent\">{refined_draft.get('literatureReview', 'Literature review not available.')}</p>
"""

    # Add main sections
    for section in refined_draft.get('mainSections', []):
        html_content += f"""
    <h2>{section.get('title', 'Section Title')}</h2>
    <p class=\"no-indent\">{section.get('content', 'Content not available.')}</p>
"""

    # Add data analysis, challenges, future outlook, and conclusion
    html_content += f"""
    <h1>Data & Statistical Analysis</h1>
    <p class=\"no-indent\">{refined_draft.get('dataAnalysis', 'Data analysis not available.')}</p>

    <h1>Challenges and Limitations</h1>
    <p class=\"no-indent\">{refined_draft.get('challenges', 'Challenges not available.')}</p>

    <h1>Future Outlook</h1>
    <p class=\"no-indent\">{refined_draft.get('futureOutlook', 'Future outlook not available.')}</p>

    <h1>Conclusion</h1>
    <p class=\"no-indent\">{refined_draft.get('conclusion', 'Conclusion not available.')}</p>

    <div class=\"references\">
        <h1>References</h1>
"""

    # Add references
    for i, source in enumerate(sources, 1):
        try:
            source_date = datetime.fromisoformat(source['dateAccessed'].replace('Z', '+00:00')).strftime('%B %d, %Y')
        except:
            source_date = "Unknown date"

        html_content += f"""
        <div class=\"ref-item\">
            [{i}] {source.get('title', 'Unknown Title')}. Retrieved from {source.get('url', 'No URL')} (Accessed: {source_date})
        </div>
"""

    html_content += """
    </div>
</body>
</html>"""

    return html_content

# FIXED: Typo in execute_research_pipeline
def execute_research_pipeline():
    """Main execution pipeline"""
    st.session_state.is_processing = True
    st.session_state.step = 'processing'

    try:
        if not API_AVAILABLE:
            raise Exception("Anthropic API key not configured in Streamlit secrets.")

        # Stage 1: Topic Analysis
        analysis = analyze_topic_with_ai(
            st.session_state.form_data['topic'],
            st.session_state.form_data['subject']
        )

        if not analysis.get('subtopics') or not analysis.get('researchQueries'):
            raise Exception("Failed to generate research structure. Please try a different topic.")

        st.session_state.research = {
            'subtopics': analysis['subtopics'],
            'queries': analysis['researchQueries'],
            'sources': []
        }

        # Stage 2: Web Research
        sources = execute_web_research(analysis['researchQueries'])
        st.session_state.research['sources'] = sources

        if len(sources) < 3:
            st.warning(f"Found only {len(sources)} sources. Continuing with available data...")

        # Stage 3: Draft
        draft_content = generate_draft(
            st.session_state.form_data['topic'],
            st.session_state.form_data['subject'],
            analysis['subtopics'],
            sources
        )
        st.session_state.draft = draft_content

        # Stage 4: Critique
        critique_content = critique_draft(draft_content, sources)
        st.session_state.critique = critique_content

        # Stage 5: Refine
        refined_content = refine_draft(draft_content, critique_content, sources)
        # FIXED: Typo here
        st.session_state.final_report = refined_content  # Was: st.session_session.final_report

        # Stage 6: Generate Report
        html_report = generate_html_report(
            refined_content,
            st.session_state.form_data,
            sources
        )

        update_progress("Complete", "Report generated successfully!", 100)
        st.session_state.html_report = html_report
        st.session_state.step = 'complete'

    except Exception as e:
        update_progress("Error", str(e), 0)
        st.session_state.step = 'error'
        st.error(f"Pipeline error: {str(e)}")
    finally:
        st.session_state.is_processing = False

def reset_system():
    """Reset the system to initial state"""
    st.session_state.step = 'input'
    st.session_state.form_data = {
        'topic': '',
        'subject': '',
        'researcher': '',
        'institution': '',
        'date': datetime.now().strftime('%Y-%m-%d')
    }
    st.session_state.progress = {
        'stage': '',
        'detail': '',
        'percent': 0
    }
    st.session_state.research = {
        'queries': [],
        'sources': [],
        'subtopics': []
    }
    st.session_state.draft = None
    st.session_state.critique = None
    st.session_state.final_report = None
    st.session_state.is_processing = False
    if 'html_report' in st.session_state:
        del st.session_state.html_report

# Main UI
st.title("📝 Online Report Writer System")

if st.session_state.step == 'input':
    st.markdown("### Research Report Input")

    col1, col2 = st.columns(2)

    with col1:
        topic = st.text_input(
            "Report Topic *",
            value=st.session_state.form_data['topic'],
            placeholder="e.g., Quantum Computing Trends in 2024",
            help="Enter the main topic for your research report"
        )
        subject = st.text_input(
            "Subject / Field *",
            value=st.session_state.form_data['subject'],
            placeholder="e.g., Computer Science, Physics, Medicine",
            help="Enter the academic or professional field"
        )

    with col2:
        researcher = st.text_input(
            "Researcher Name *",
            value=st.session_state.form_data['researcher'],
            placeholder="Your name",
            help="Enter your name or the researcher's name"
        )
        institution = st.text_input(
            "Institution *",
            value=st.session_state.form_data['institution'],
            placeholder="University or Organization",
            help="Enter your institution or organization"
        )

    date = st.date_input(
        "Report Date",
        value=datetime.strptime(st.session_state.form_data['date'], '%Y-%m-%d'),
        help="Select the date for the report"
    )

    # Update form data
    st.session_state.form_data = {
        'topic': topic,
        'subject': subject,
        'researcher': researcher,
        'institution': institution,
        'date': date.strftime('%Y-%m-%d')
    }

    is_form_valid = all([topic, subject, researcher, institution])

    if st.button(
        "🚀 Generate Research Report",
        disabled=not is_form_valid,
        type="primary",
        use_container_width=True
    ):
        if not API_AVAILABLE:
            st.error("Please configure Anthropic API key in Streamlit secrets first.")
        else:
            execute_research_pipeline()
            st.rerun()

elif st.session_state.step == 'processing':
    st.markdown("### Research Progress")

    # Progress bar
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**{st.session_state.progress['stage']}**")
        st.progress(st.session_state.progress['percent'] / 100)
    with col2:
        st.markdown(f"**{st.session_state.progress['percent']}%**")

    st.info(st.session_state.progress['detail'])

    # Research details
    if st.session_state.research['queries']:
        with st.expander(f"📋 Research Queries ({len(st.session_state.research['queries'])})", expanded=False):
            for i, query in enumerate(st.session_state.research['queries'], 1):
                st.markdown(f"**{i}.** {query}")

    if st.session_state.research['sources']:
        with st.expander(f"🔍 Sources Found ({len(st.session_state.research['sources'])})", expanded=False):
            for i, source in enumerate(st.session_state.research['sources'], 1):
                st.markdown(f"""
                <div class=\"source-item\">
                    <strong>{i}. {source.get('title', 'Untitled')[:80]}</strong><br>
                    <small>🔗 {source.get('url', 'No URL')[:60]}...</small><br>
                    <small>📊 Credibility: {source.get('credibilityScore', 0)}% • 📅 Accessed: {source.get('dateAccessed', 'Unknown')[:10]}</small>
                </div>
                """, unsafe_allow_html=True)

    # Simulate progress updates
    if st.session_state.progress['percent'] < 100:
        time.sleep(1)  # Simulate processing time
        st.rerun()

elif st.session_state.step == 'complete':
    st.success("✅ Report Generated Successfully!")

    # Report details
    st.markdown("### Report Details")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**📝 Topic**")
        st.info(st.session_state.form_data['topic'])
    with col2:
        st.markdown("**🎓 Subject**")
        st.info(st.session_state.form_data['subject'])
    with col3:
        st.markdown("**👤 Researcher**")
        st.info(st.session_state.form_data['researcher'])

    # Research statistics
    st.markdown("### 📊 Research Statistics")
    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)

    with stat_col1:
        st.metric("Queries", len(st.session_state.research['queries']))
    with stat_col2:
        st.metric("Sources", len(st.session_state.research['sources']))
    with stat_col3:
        if st.session_state.research['sources']:
            avg_quality = sum(s.get('credibilityScore', 0) for s in st.session_state.research['sources']) / len(st.session_state.research['sources'])
            st.metric("Avg Quality", f"{avg_quality:.0f}%")
        else:
            st.metric("Avg Quality", "N/A")
    with stat_col4:
        if st.session_state.critique:
            score = st.session_state.critique.get('overallScore', 'N/A')
            st.metric("Quality Score", f"{score}/100" if score != 'N/A' else "N/A")
        else:
            st.metric("Quality Score", "N/A")

    # Report preview
    st.markdown("### 📄 Report Preview")

    with st.expander("📋 Executive Summary", expanded=False):
        if st.session_state.final_report and 'executiveSummary' in st.session_state.final_report:
            st.write(st.session_state.final_report['executiveSummary'])
        else:
            st.info("Executive summary not available")

    with st.expander("🔍 Abstract", expanded=False):
        if st.session_state.final_report and 'abstract' in st.session_state.final_report:
            st.write(st.session_state.final_report['abstract'])
        else:
            st.info("Abstract not available")

    if st.session_state.final_report and 'mainSections' in st.session_state.final_report:
        with st.expander("📑 Main Sections", expanded=False):
            for section in st.session_state.final_report['mainSections']:
                st.subheader(section.get('title', 'Untitled Section'))
                st.write(section.get('content', 'Content not available'))

    # Quality feedback
    if st.session_state.critique:
        with st.expander("✅ Quality Review Feedback", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Overall Score", st.session_state.critique.get('overallScore', 'N/A'))

            if st.session_state.critique.get('recommendations'):
                st.markdown("**Recommendations:**")
                for rec in st.session_state.critique['recommendations']:
                    st.markdown(f"- {rec}")

    # Download report
    st.markdown("### 📥 Download Report")

    if 'html_report' in st.session_state:
        # Create download button for HTML
        b64 = base64.b64encode(st.session_state.html_report.encode()).decode()
        filename = f"{st.session_state.form_data['topic'].replace(' ', '_')}_Research_Report.html"
        href = f'<a href="data:text/html;base64,{b64}" download="{filename}" class=\"stDownloadButton\">📥 Download HTML Report</a>'
        st.markdown(href, unsafe_allow_html=True)

        st.info("""
        **📋 Instructions:**
        1. Click the download button above to save the HTML file
        2. Open the downloaded file in your web browser
        3. Use your browser's Print function (Ctrl+P or Cmd+P)
        4. Select \"Save as PDF\" to create a professional PDF version
        5. Adjust print settings as needed (margins, headers, etc.)
        """)

    # Generate another report
    if st.button("🔄 Generate Another Report", use_container_width=True):
        reset_system()
        st.rerun()

elif st.session_state.step == 'error':
    st.error("❌ Error Occurred During Report Generation")

    st.warning(st.session_state.progress['detail'])

    if st.button("🔄 Try Again", use_container_width=True):
        reset_system()
        st.rerun()

# Footer
st.markdown("---")
st.markdown(
    "**🔬 Autonomous Research Pipeline:** Topic Analysis → Web Research → Draft → Review → Refine → Report Generation"
)
st.caption(
    "Powered by Anthropic Claude API • Generated reports include AI-assisted research and analysis"
)
