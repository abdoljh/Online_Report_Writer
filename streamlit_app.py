import streamlit as st
import json
import requests
import time
from datetime import datetime
import base64
from io import BytesIO
import tempfile
import os

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

# API Configuration (Replace with your actual API keys)
ANTHROPIC_API_KEY = st.sidebar.text_input("Anthropic API Key", type="password")
USE_MOCK_DATA = st.sidebar.checkbox("Use Mock Data (No API Calls)", value=True)

def update_progress(stage, detail, percent):
    """Update progress in session state"""
    st.session_state.progress = {
        'stage': stage,
        'detail': detail,
        'percent': percent
    }

def calculate_credibility(url):
    """Calculate credibility score based on domain"""
    if '.gov' in url or '.edu' in url:
        return 95
    if 'nature.com' in url or 'science.org' in url:
        return 95
    if 'ieee.org' in url or 'acm.org' in url:
        return 90
    if '.org' in url:
        return 85
    return 80

# Mock data for testing
def get_mock_analysis():
    return {
        "subtopics": [
            "Introduction to Quantum Computing",
            "Current State of Quantum Processors",
            "Quantum Algorithms and Applications",
            "Challenges in Quantum Error Correction",
            "Commercial Quantum Computing Services",
            "Future Trends and Predictions"
        ],
        "researchQueries": [
            "latest developments in quantum computing 2024",
            "quantum supremacy recent achievements",
            "quantum error correction techniques",
            "commercial quantum computing companies",
            "quantum algorithms practical applications"
        ]
    }

def get_mock_sources():
    return [
        {
            "title": "Quantum Computing: Current State and Future Prospects",
            "url": "https://arxiv.org/abs/quant-ph/2401.01234",
            "content": "Recent advances in quantum computing have shown promising results...",
            "query": "latest developments in quantum computing 2024",
            "credibilityScore": 90,
            "dateAccessed": datetime.now().isoformat()
        },
        {
            "title": "Quantum Error Correction: A Comprehensive Review",
            "url": "https://www.nature.com/articles/s41534-023-00765-z",
            "content": "Error correction remains a major challenge in quantum computing...",
            "query": "quantum error correction techniques",
            "credibilityScore": 95,
            "dateAccessed": datetime.now().isoformat()
        }
    ]

def get_mock_draft():
    return {
        "abstract": "This report examines the current state and future prospects of quantum computing. Quantum computing represents a paradigm shift in computational capabilities, leveraging quantum mechanical phenomena to solve complex problems that are intractable for classical computers.",
        "introduction": "The field of quantum computing has seen rapid advancements in recent years...",
        "literatureReview": "Previous research in quantum computing has focused on...",
        "mainSections": [
            {
                "title": "Quantum Computing Fundamentals",
                "content": "Quantum computers use qubits that can exist in superposition states..."
            },
            {
                "title": "Current Technological Landscape",
                "content": "Major tech companies including IBM, Google, and Microsoft are investing heavily..."
            }
        ],
        "challenges": "Despite promising advances, quantum computing faces several challenges...",
        "futureOutlook": "The next decade will likely see significant progress in quantum computing...",
        "conclusion": "Quantum computing represents a transformative technology with the potential to revolutionize..."
    }

def get_mock_critique():
    return {
        "factIssues": ["Need more specific data on qubit count improvements"],
        "flowIssues": ["Transition between sections could be smoother"],
        "unsupportedClaims": ["Claim about quantum advantage needs citation"],
        "biasFlags": [],
        "structuralWeaknesses": ["Executive summary missing"],
        "citationIssues": ["Some sources not properly referenced"],
        "overallScore": 78,
        "recommendations": ["Add executive summary", "Include more recent data", "Improve citation format"]
    }

def get_mock_refined():
    draft = get_mock_draft()
    draft["executiveSummary"] = "This comprehensive report analyzes the current state of quantum computing technology, examining recent advancements, challenges, and future prospects. The analysis covers key developments in quantum hardware, software, and algorithms, providing insights into the commercial and research landscape."
    return draft

# Simulated pipeline functions
def simulate_topic_analysis(topic, subject):
    """Simulate topic analysis"""
    update_progress("Topic Analysis", "Decomposing topic into research dimensions...", 10)
    time.sleep(2)
    return get_mock_analysis()

def simulate_web_research(queries):
    """Simulate web research"""
    update_progress("Web Research", f"Executing {len(queries)} parallel searches...", 25)
    time.sleep(3)
    return get_mock_sources()

def simulate_draft_generation(topic, subject, subtopics, sources):
    """Simulate draft generation"""
    update_progress("Drafting", "Synthesizing research into comprehensive report...", 45)
    time.sleep(2)
    return get_mock_draft()

def simulate_critique(draft, sources):
    """Simulate critique"""
    update_progress("Review", "Critical analysis by reviewer agent...", 65)
    time.sleep(2)
    return get_mock_critique()

def simulate_refinement(draft, critique, sources):
    """Simulate refinement"""
    update_progress("Refinement", "Applying editorial improvements...", 80)
    time.sleep(2)
    return get_mock_refined()

def generate_html_report(refined_draft, form_data, sources):
    """Generate HTML report"""
    update_progress("PDF Generation", "Creating professional document...", 95)
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{form_data['topic']} - Research Report</title>
    <style>
        @page {{ margin: 1in; }}
        body {{
            font-family: 'Times New Roman', serif;
            font-size: 12pt;
            line-height: 1.6;
            color: #000;
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
        h1 {{ font-size: 18pt; margin-top: 0.5in; }}
        h2 {{ font-size: 14pt; margin-top: 0.3in; }}
        p {{ text-align: justify; margin: 0.15in 0; }}
        .abstract {{
            font-style: italic;
            margin: 0.25in 1in;
        }}
        .references {{
            page-break-before: always;
        }}
        .ref-item {{
            margin: 0.15in 0 0.15in 0.5in;
            text-indent: -0.5in;
        }}
    </style>
</head>
<body>
    <div class="cover">
        <h1>{form_data['topic']}</h1>
        <div class="meta">A Research Report</div>
        <div class="meta">Subject: {form_data['subject']}</div>
        <div class="meta" style="margin-top: 1in;">
            Prepared by<br>
            {form_data['researcher']}<br>
            {form_data['institution']}<br>
            {form_data['date']}
        </div>
    </div>

    <h1>Executive Summary</h1>
    <p>{refined_draft.get('executiveSummary', 'Executive summary pending...')}</p>

    <h1>Abstract</h1>
    <div class="abstract">{refined_draft.get('abstract', '')}</div>

    <h1>Introduction</h1>
    <p>{refined_draft.get('introduction', '')}</p>

    <h1>Literature Review</h1>
    <p>{refined_draft.get('literatureReview', '')}</p>
"""

    # Add main sections
    for section in refined_draft.get('mainSections', []):
        html_content += f"""
    <h2>{section.get('title', '')}</h2>
    <p>{section.get('content', '')}</p>
"""

    html_content += f"""
    <h1>Challenges and Limitations</h1>
    <p>{refined_draft.get('challenges', '')}</p>

    <h1>Future Outlook</h1>
    <p>{refined_draft.get('futureOutlook', '')}</p>

    <h1>Conclusion</h1>
    <p>{refined_draft.get('conclusion', '')}</p>

    <div class="references">
        <h1>References</h1>
"""

    # Add references
    for i, source in enumerate(sources, 1):
        date = datetime.fromisoformat(source['dateAccessed']).strftime('%B %d, %Y')
        html_content += f"""
        <div class="ref-item">
            [{i}] {source['title']}. Retrieved from {source['url']} (Accessed: {date})
        </div>
"""

    html_content += """
    </div>
</body>
</html>"""
    
    return html_content

def execute_research_pipeline():
    """Main execution pipeline"""
    st.session_state.is_processing = True
    st.session_state.step = 'processing'
    
    try:
        # Stage 1: Topic Analysis
        analysis = simulate_topic_analysis(
            st.session_state.form_data['topic'],
            st.session_state.form_data['subject']
        )
        st.session_state.research = {
            'subtopics': analysis['subtopics'],
            'queries': analysis['researchQueries'],
            'sources': []
        }
        
        # Stage 2: Web Research
        sources = simulate_web_research(analysis['researchQueries'])
        st.session_state.research['sources'] = sources
        
        if len(sources) < 2:
            raise Exception('Insufficient quality sources found. Please try a different topic.')
        
        # Stage 3: Draft
        draft_content = simulate_draft_generation(
            st.session_state.form_data['topic'],
            st.session_state.form_data['subject'],
            analysis['subtopics'],
            sources
        )
        st.session_state.draft = draft_content
        
        # Stage 4: Critique
        critique_content = simulate_critique(draft_content, sources)
        st.session_state.critique = critique_content
        
        # Stage 5: Refine
        refined_content = simulate_refinement(draft_content, critique_content, sources)
        st.session_state.final_report = refined_content
        
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
            placeholder="e.g., Quantum Computing Trends in 2024"
        )
        subject = st.text_input(
            "Subject / Field *",
            value=st.session_state.form_data['subject'],
            placeholder="e.g., Computer Science, Physics, Medicine"
        )
    
    with col2:
        researcher = st.text_input(
            "Researcher Name *",
            value=st.session_state.form_data['researcher'],
            placeholder="Your name"
        )
        institution = st.text_input(
            "Institution *",
            value=st.session_state.form_data['institution'],
            placeholder="University or Organization"
        )
    
    date = st.date_input(
        "Date",
        value=datetime.strptime(st.session_state.form_data['date'], '%Y-%m-%d')
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
        with st.expander(f"Research Queries ({len(st.session_state.research['queries'])})"):
            for i, query in enumerate(st.session_state.research['queries'], 1):
                st.markdown(f"{i}. {query}")
    
    if st.session_state.research['sources']:
        with st.expander(f"Trusted Sources Found ({len(st.session_state.research['sources'])})"):
            for source in st.session_state.research['sources']:
                st.markdown(f"""
                <div class="source-item">
                    <strong>{source['title']}</strong><br>
                    <small>URL: {source['url']}</small><br>
                    <small>Credibility: {source['credibilityScore']}% • Query: {source['query']}</small>
                </div>
                """, unsafe_allow_html=True)
    
    # Simulate processing delay
    if st.session_state.progress['percent'] < 100:
        time.sleep(0.5)
        st.rerun()

elif st.session_state.step == 'complete':
    st.success("✅ Report Generated Successfully!")
    
    # Report details
    st.markdown("### Report Details")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Topic**")
        st.info(st.session_state.form_data['topic'])
    with col2:
        st.markdown("**Subject**")
        st.info(st.session_state.form_data['subject'])
    with col3:
        st.markdown("**Researcher**")
        st.info(st.session_state.form_data['researcher'])
    
    # Research statistics
    st.markdown("### Research Statistics")
    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
    
    with stat_col1:
        st.metric("Queries", len(st.session_state.research['queries']))
    with stat_col2:
        st.metric("Sources", len(st.session_state.research['sources']))
    with stat_col3:
        avg_quality = sum(s['credibilityScore'] for s in st.session_state.research['sources']) / len(st.session_state.research['sources'])
        st.metric("Avg Quality", f"{avg_quality:.0f}%")
    with stat_col4:
        if st.session_state.critique:
            st.metric("Quality Score", f"{st.session_state.critique.get('overallScore', 'N/A')}/100")
    
    # Report preview
    st.markdown("### Report Preview")
    with st.expander("Executive Summary"):
        if st.session_state.final_report and 'executiveSummary' in st.session_state.final_report:
            st.write(st.session_state.final_report['executiveSummary'])
    
    with st.expander("Abstract"):
        if st.session_state.final_report and 'abstract' in st.session_state.final_report:
            st.write(st.session_state.final_report['abstract'])
    
    with st.expander("Main Sections"):
        if st.session_state.final_report and 'mainSections' in st.session_state.final_report:
            for section in st.session_state.final_report['mainSections']:
                st.subheader(section['title'])
                st.write(section['content'])
    
    # Download report
    st.markdown("### Download Report")
    if 'html_report' in st.session_state:
        # Create download button for HTML
        b64 = base64.b64encode(st.session_state.html_report.encode()).decode()
        filename = f"{st.session_state.form_data['topic'].replace(' ', '_')}_Report.html"
        href = f'<a href="data:text/html;base64,{b64}" download="{filename}" class="stDownloadButton">📥 Download HTML Report</a>'
        st.markdown(href, unsafe_allow_html=True)
        
        st.info("""
        **Instructions:** 
        1. Download the HTML file above
        2. Open it in your web browser
        3. Use your browser's Print function (Ctrl+P)
        4. Select "Save as PDF" to create a PDF version
        """)
    
    # Generate another report
    if st.button("🔄 Generate Another Report", use_container_width=True):
        reset_system()
        st.rerun()

elif st.session_state.step == 'error':
    st.error("❌ Error Occurred")
    st.warning(st.session_state.progress['detail'])
    
    if st.button("🔄 Try Again", use_container_width=True):
        reset_system()
        st.rerun()

# Footer
st.markdown("---")
st.markdown(
    "**Autonomous Research Pipeline:** Topic Analysis → Web Research → Draft → Review → Refine → Report Generation"
)
st.caption(
    "Note: This is a simulation version using mock data. For full functionality, "
    "configure API keys in the sidebar and disable 'Use Mock Data'."
)
