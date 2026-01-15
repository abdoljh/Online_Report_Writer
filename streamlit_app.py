import streamlit as st
import requests
import json
from datetime import datetime

# --- System Configuration ---
st.set_page_config(page_title="Online Report Writer", layout="wide")

def calculate_credibility(url):
    [span_4](start_span)"""Calculates credibility score based on domain[span_4](end_span)."""
    if '.gov' in url or '.edu' in url: 
        return 95
    if 'nature.com' in url or 'science.org' in url: 
        return 95
    if 'ieee.org' in url or 'acm.org' in url: 
        return 90
    if '.org' in url: 
        return 85
    return 80

# -[span_5](start_span)-- UI Header[span_5](end_span) ---
st.title("📄 Online Report Writer System")
st.markdown("---")

# -[span_6](start_span)[span_7](start_span)[span_8](start_span)-- Session State Initialization[span_6](end_span)[span_7](end_span)[span_8](end_span) ---
if 'step' not in st.session_state:
    st.session_state.step = 'input'
if 'formData' not in st.session_state:
    st.session_state.formData = {
        'topic': '', 'subject': '', 'researcher': '', 
        'institution': '', 'date': str(datetime.now().date())
    }

# -[span_9](start_span)[span_10](start_span)[span_11](start_span)[span_12](start_span)-- Step 1: Input Form[span_9](end_span)[span_10](end_span)[span_11](end_span)[span_12](end_span) ---
if st.session_state.step == 'input':
    with st.container():
        st.subheader("Report Parameters")
        st.session_state.formData['topic'] = st.text_input("Report Topic *", placeholder="e.g., Quantum Computing Trends in 2026")
        st.session_state.formData['subject'] = st.text_input("Subject / Field *", placeholder="e.g., Computer Science")
        st.session_state.formData['researcher'] = st.text_input("Researcher Name *")
        st.session_state.formData['institution'] = st.text_input("Institution *")
        
        is_valid = all([st.session_state.formData['topic'], st.session_state.formData['subject'], 
                        st.session_state.formData['researcher'], st.session_state.formData['institution']])
        
        if st.button("Generate Research Report", disabled=not is_valid):
            st.session_state.step = 'processing'
            st.rerun()

# -[span_13](start_span)[span_14](start_span)[span_15](start_span)-- Step 2: Processing Pipeline[span_13](end_span)[span_14](end_span)[span_15](end_span) ---
elif st.session_state.step == 'processing':
    st.info("Pipeline Execution: Analysis → Research → Draft → Review → Refine")
    progress_bar = st.progress(0)
    status = st.empty()

    try:
        # 1. [span_16](start_span)Topic Analysis[span_16](end_span)
        status.markdown("🔍 **Stage 1: Topic Analysis** - Decomposing research dimensions...")
        progress_bar.progress(10)
        # (AI API call logic would go here)
        
        # 2. [span_17](start_span)Web Research[span_17](end_span)
        status.markdown("🌐 **Stage 2: Web Research** - Executing parallel searches...")
        progress_bar.progress(25)
        
        # 3. [span_18](start_span)Draft Generation[span_18](end_span)
        status.markdown("✍️ **Stage 3: Drafting** - Synthesizing report...")
        progress_bar.progress(45)
        
        # 4. [span_19](start_span)Critique[span_19](end_span)
        status.markdown("🧐 **Stage 4: Review** - AI Critique for accuracy and bias...")
        progress_bar.progress(65)
        
        # 5. [span_20](start_span)Refinement[span_20](end_span)
        status.markdown("🔧 **Stage 5: Refinement** - Improving academic tone...")
        progress_bar.progress(85)
        
        # 6. [span_21](start_span)PDF Generation[span_21](end_span)
        status.markdown("🖨️ **Stage 6: Finalizing** - Creating professional document...")
        progress_bar.progress(100)
        
        st.session_state.step = 'complete'
        st.rerun()
        
    except Exception as e:
        st.error(f"Pipeline Error: {str(e)}")
        if st.button("Try Again"):
            st.session_state.step = 'input'
            st.rerun()

# -[span_22](start_span)[span_23](start_span)-- Step 3: Completion[span_22](end_span)[span_23](end_span) ---
elif st.session_state.step == 'complete':
    st.success("Report Generated Successfully!")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Topic", st.session_state.formData['topic'])
        st.metric("Researcher", st.session_state.formData['researcher'])
    
    st.download_button(
        label="Download HTML Report",
        data="<html><body><h1>Report Content Placeholder</h1></body></html>",
        file_name=f"{st.session_state.formData['topic'].replace(' ', '_')}_Report.html",
        mime="text/html"
    )
    
    if st.button("Generate Another Report"):
        st.session_state.step = 'input'
        st.rerun()
