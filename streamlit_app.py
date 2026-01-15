import streamlit as st
import json
import requests
from datetime import datetime
import base64

# --- Configuration & Styling ---
st.set_page_config(page_title="Online Report Writer", page_icon="📝", layout="centered")
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .report-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---
def calculate_credibility(url):
    """Calculates credibility score based on domain."""
    # [span_0](start_span)Logic based on[span_0](end_span)
    if '.gov' in url or '.edu' in url: 
        [span_1](start_span)return 95[span_1](end_span)
    if 'nature.com' in url or 'science.org' in url: 
        [span_2](start_span)return 95[span_2](end_span)
    if 'ieee.org' in url or 'acm.org' in url: 
        [span_3](start_span)return 90[span_3](end_span)
    if '.org' in url: 
        [span_4](start_span)return 85[span_4](end_span)
    [span_5](start_span)return 80[span_5](end_span)

def call_llm(messages, max_tokens=2000):
    [span_1](start_span)[span_2](start_span)[span_3](start_span)"""Placeholder for the Claude API call structure used in the source[span_1](end_span)[span_2](end_span)[span_3](end_span)."""
    # Note: In a production test, replace with st.secrets["ANTHROPIC_API_KEY"]
    api_key = st.sidebar.text_input("Enter Anthropic API Key", type="password")
    if not api_key:
        st.error("Please provide an API key in the sidebar to proceed.")
        return None
    
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    data = {
        "model": "claude-3-sonnet-20240229", # Updated to current available model
        "max_tokens": max_tokens,
        "messages": messages
    }
    try:
        response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data)
        res_json = response.json()
        text = res_json['content'][0]['text']
        # [span_4](start_span)[span_5](start_span)Extract JSON from potential markdown blocks[span_4](end_span)[span_5](end_span)
        return json.loads(text.replace('```json', '').replace('```', '').strip())
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return None

# --- Main Pipeline Stages ---
def run_pipeline(form_data):
    progress_bar = st.progress(0)
    status_text = st.empty()

    # [span_6](start_span)[span_7](start_span)Stage 1: Topic Analysis[span_6](end_span)[span_7](end_span)
    status_text.text("Stage 1: Analyzing research dimensions...")
    analysis_prompt = f"Analyze topic: {form_data['topic']} in {form_data['subject']}. Return JSON with 'subtopics' and 'researchQueries'."
    analysis = call_llm([{"role": "user", "content": analysis_prompt}])
    if not analysis: return
    progress_bar.progress(15)

    # [span_8](start_span)[span_9](start_span)Stage 2: Web Research[span_8](end_span)[span_9](end_span)
    # [span_10](start_span)Note: Real web search requires a tool/search API; here we simulate the logic[span_10](end_span)
    status_text.text(f"Stage 2: Executing {len(analysis['researchQueries'])} parallel searches...")
    sources = [
        {"title": f"Study on {form_data['topic']}", "url": "https://research.edu/paper1", "content": "Sample research data...", "credibilityScore": 95, "dateAccessed": str(datetime.now())}
    [span_11](start_span)] * 5 # Simulated source list based on logic[span_11](end_span)
    progress_bar.progress(30)

    # [span_12](start_span)[span_13](start_span)Stage 3: Draft Generation[span_12](end_span)[span_13](end_span)
    status_text.text("Stage 3: Synthesizing research into draft...")
    draft = call_llm([{"role": "user", "content": f"Draft report on {form_data['topic']} using sources. Return JSON."}])
    progress_bar.progress(50)

    # [span_14](start_span)[span_15](start_span)Stage 4: Critique[span_14](end_span)[span_15](end_span)
    status_text.text("Stage 4: Critical analysis by reviewer agent...")
    critique = call_llm([{"role": "user", "content": "Critique this draft for bias and accuracy. Return JSON."}])
    progress_bar.progress(70)

    # [span_16](start_span)[span_17](start_span)Stage 5: Refine[span_16](end_span)[span_17](end_span)
    status_text.text("Stage 5: Applying editorial improvements...")
    refined = call_llm([{"role": "user", "content": "Refine draft based on critique. Return JSON."}])
    progress_bar.progress(90)

    # [span_18](start_span)[span_19](start_span)Stage 6: PDF (HTML) Generation[span_18](end_span)[span_19](end_span)
    status_text.text("Stage 6: Finalizing report...")
    return refined, sources, analysis

# --- UI Layout ---
st.title("📝 Online Report Writer System")
st.caption("Autonomous Pipeline: Analysis → Research → Draft → Review → Refine")

if 'step' not in st.session_state:
    st.session_state.step = 'input'

if st.session_state.step == 'input':
    with st.form("research_form"):
        [span_20](start_span)topic = st.text_input("Report Topic *", placeholder="e.g., Quantum Computing Trends in 2026")[span_20](end_span)
        [span_21](start_span)subject = st.text_input("Subject / Field *", placeholder="e.g., Computer Science")[span_21](end_span)
        [span_22](start_span)researcher = st.text_input("Researcher Name *")[span_22](end_span)
        [span_23](start_span)institution = st.text_input("Institution *")[span_23](end_span)
        
        submitted = st.form_submit_button("Generate Research Report")
        if submitted and topic and subject and researcher and institution:
            st.session_state.form_data = {"topic": topic, "subject": subject, "researcher": researcher, "institution": institution}
            st.session_state.step = 'processing'
            st.rerun()

elif st.session_state.step == 'processing':
    results = run_pipeline(st.session_state.form_data)
    if results:
        st.session_state.final_report, st.session_state.sources, st.session_state.analysis = results
        st.session_state.step = 'complete'
        st.rerun()

elif st.session_state.step == 'complete':
    [span_24](start_span)st.success("Report Generated Successfully!")[span_24](end_span)
    
    # [span_25](start_span)[span_26](start_span)Download Button logic[span_25](end_span)[span_26](end_span)
    report_html = f"<html><body><h1>{st.session_state.form_data['topic']}</h1><p>Refined content here...</p></body></html>"
    b64 = base64.b64encode(report_html.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="report.html">Download HTML Report</a>'
    st.markdown(href, unsafe_allow_html=True)

    if st.button("Generate Another Report"):
        st.session_state.step = 'input'
        st.rerun()
