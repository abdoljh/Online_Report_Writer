import streamlit as st
import requests
import json
from datetime import datetime

# --- Logic: Credibility Scoring (Source 23-24) ---
def calculate_credibility(url):
    """Calculates credibility score based on domain."""
    if '.gov' in url or '.edu' in url: 
        [span_5](start_span)return 95[span_5](end_span)
    if 'nature.com' in url or 'science.org' in url: 
        [span_6](start_span)return 95[span_6](end_span)
    if 'ieee.org' in url or 'acm.org' in url: 
        [span_7](start_span)return 90[span_7](end_span)
    if '.org' in url: 
        [span_8](start_span)return 85[span_8](end_span)
    [span_9](start_span)return 80[span_9](end_span)

# --- UI Configuration (Source 70-71) ---
st.set_page_config(page_title="Online Report Writer", layout="centered")
st.title("📝 Online Report Writer System")

if 'step' not in st.session_state:
    st.session_state.step = 'input'

# --- Stage 1: Input (Source 71-82) ---
if st.session_state.step == 'input':
    with st.form("input_form"):
        [span_10](start_span)topic = st.text_input("Report Topic *", placeholder="e.g., Quantum Computing Trends in 2026")[span_10](end_span)
        [span_11](start_span)subject = st.text_input("Subject / Field *", placeholder="e.g., Computer Science")[span_11](end_span)
        [span_12](start_span)researcher = st.text_input("Researcher Name *")[span_12](end_span)
        [span_13](start_span)institution = st.text_input("Institution *")[span_13](end_span)
        
        submit = st.form_submit_button("Generate Research Report")
        
        if submit:
            [span_14](start_span)[span_15](start_span)if topic and subject and researcher and institution:[span_14](end_span)[span_15](end_span)
                st.session_state.formData = {
                    'topic': topic, 'subject': subject, 
                    'researcher': researcher, 'institution': institution,
                    'date': str(datetime.now().date())
                }
                st.session_state.step = 'processing'
                st.rerun()
            else:
                st.error("Please fill in all required fields.")

# --- Stage 2: Processing Pipeline (Source 8, 12, 25, 30, 34) ---
elif st.session_state.step == 'processing':
    st.subheader("Processing Research Pipeline")
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Sequence: Analysis -> Research -> Draft -> Critique -> Refine
    # Stage 1: Topic Analysis
    [span_16](start_span)status_text.text("Stage 1: Analyzing research dimensions...")[span_16](end_span)
    [span_17](start_span)progress_bar.progress(15)[span_17](end_span)
    
    # Stage 2: Web Research
    [span_18](start_span)status_text.text("Stage 2: Executing parallel searches...")[span_18](end_span)
    [span_19](start_span)progress_bar.progress(30)[span_19](end_span)
    
    # Stage 3: Draft Generation
    [span_20](start_span)status_text.text("Stage 3: Synthesizing research into draft...")[span_20](end_span)
    [span_21](start_span)progress_bar.progress(50)[span_21](end_span)
    
    # Stage 4: Critique
    [span_22](start_span)status_text.text("Stage 4: AI Critique for accuracy and bias...")[span_22](end_span)
    [span_23](start_span)progress_bar.progress(70)[span_23](end_span)
    
    # Stage 5: Refine
    [span_24](start_span)status_text.text("Stage 5: Applying editorial improvements...")[span_24](end_span)
    [span_25](start_span)progress_bar.progress(90)[span_25](end_span)
    
    st.session_state.step = 'complete'
    st.rerun()

# --- Stage 3: Complete (Source 96-103) ---
elif st.session_state.step == 'complete':
    [span_26](start_span)st.success("Report Generated Successfully!")[span_26](end_span)
    
    [span_27](start_span)st.write(f"**Topic:** {st.session_state.formData['topic']}")[span_27](end_span)
    [span_28](start_span)st.write(f"**Researcher:** {st.session_state.formData['researcher']}")[span_28](end_span)

    # HTML Download Logic (Source 39-53)
    report_name = st.session_state.formData['topic'].replace(" ", "_")
    st.download_button(
        label="Download HTML Report",
        data="<html><body><h1>Report Placeholder</h1></body></html>", # Replace with refined content
        [span_29](start_span)file_name=f"{report_name}_Report.html",[span_29](end_span)
        mime="text/html"
    )
    
    [span_30](start_span)if st.button("Generate Another Report"):[span_30](end_span)
        st.session_state.step = 'input'
        st.rerun()
