# streamlit_app.py
# Enterprise Version 2.0
# ChatGPT
# Jan. 16, 2026

import os
import json
import asyncio
import uuid
import datetime
import requests
from dataclasses import dataclass, asdict
from typing import List, Dict
from pathlib import Path
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from jinja2 import Template
import openai
import streamlit as st
from weasyprint import HTML

# ============================
# ENVIRONMENT
# ============================

# Get API key from Streamlit Secrets
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY")
BING_API_KEY = st.secrets.get("BING_API_KEY")
SEARCH_PROVIDER = st.secrets.get("SEARCH_PROVIDER", "serpapi")
PDF_ENGINE = st.secrets.get("PDF_ENGINE", "weasyprint")

# Check if they exist
if not OPENAI_API_KEY or not BING_API_KEY or not SEARCH_PROVIDER or not PDF_ENGINE:
    st.error("Missing API keys in Streamlit Secrets!")
    raise RuntimeError("Missing API keys and/or other environment. Check Streamlit Secrets.")

# ============================
# PATHS
# ============================

# Define your base directory (the folder where your script lives)
BASE_DIR = Path(__file__).resolve().parent

# Define subdirectories
OUTPUT_DIR = BASE_DIR / "outputs"
TEMPLATE_DIR = BASE_DIR / "templates"

# Ensure the directories exist (prevents FileNotFoundError)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

# =====================
# Data Models
# =====================

@dataclass
class Source:
    id: int
    title: str
    url: str
    domain: str
    credibility_score: float

@dataclass
class ReportMetadata:
    topic: str
    subject: str
    researcher: str
    institution: str
    date: str

# =====================
# Agent Base
# =====================

class Agent:
    def __init__(self, name):
        self.name = name

# =====================
# Agents
# =====================

class TopicAnalyzerAgent(Agent):
    async def run(self, metadata):
        return {"topic": metadata.topic}

class ResearchPlannerAgent(Agent):
    async def run(self, topic):
        queries = [
            f"{topic} academic research",
            f"{topic} trends",
            f"{topic} statistics",
            f"{topic} challenges",
            f"{topic} future outlook",
            f"{topic} site:edu",
            f"{topic} site:gov",
            f"{topic} site:org"
        ]
        return {"queries": queries}

class SearchAgent(Agent):
    async def run(self, queries):
        headers = {"Ocp-Apim-Subscription-Key": BING_API_KEY}
        results = []

        for q in queries:
            url = "https://api.bing.microsoft.com/v7.0/search"
            params = {"q": q, "count": 5}
            r = requests.get(url, headers=headers, params=params, timeout=20)
            data = r.json()

            for item in data.get("webPages", {}).get("value", []):
                results.append({
                    "title": item["name"],
                    "url": item["url"],
                    "domain": item["url"].split("/")[2]
                })

        return {"raw_results": results}

class SourceValidatorAgent(Agent):
    async def run(self, raw_results):
        trusted = []
        idx = 1

        for r in raw_results:
            domain = r["domain"]
            score = 0.6
            if domain.endswith(".edu") or domain.endswith(".gov"):
                score = 0.95
            elif domain.endswith(".org"):
                score = 0.85

            if score >= 0.75:
                trusted.append(Source(
                    id=idx,
                    title=r["title"],
                    url=r["url"],
                    domain=domain,
                    credibility_score=score
                ))
                idx += 1

        return {"sources": trusted}

class KnowledgeBaseBuilderAgent(Agent):
    async def run(self, sources: List[Source]):
        facts = []

        for s in sources[:15]:
            try:
                html = requests.get(s.url, timeout=20).text
                soup = BeautifulSoup(html, "html.parser")
                text = " ".join(p.get_text() for p in soup.find_all("p")[:10])
                facts.append({
                    "source_id": s.id,
                    "text": text[:2000]
                })
            except:
                pass

        return {"facts": facts}

class WriterAgent(Agent):
    async def run(self, kb, metadata):

        prompt = f"""
Write a professional academic research report on:

Topic: {metadata.topic}

Facts:
{json.dumps(kb["facts"], indent=2)}

Sections:
Executive Summary
Abstract
Introduction
Literature Review
Main Analysis
Data & Statistics
Challenges
Future Outlook
Conclusion

Use citations like [1], [2].
"""

        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=3500
        )

        return {"draft_v1": resp.choices[0].message.content}

class CriticAgent(Agent):
    async def run(self, draft):
        prompt = f"Review this report for factual issues, coherence, structure and missing sections:\n{draft}"
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1000
        )
        return {"critic_notes": resp.choices[0].message.content}

class RefinerAgent(Agent):
    async def run(self, draft, critic):

        prompt = f"""
Improve the following report using this feedback:

Feedback:
{critic}

Report:
{draft}

Return improved report.
"""

        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.25,
            max_tokens=4000
        )

        return {"final_text": resp.choices[0].message.content}

class CitationManagerAgent(Agent):
    async def run(self, sources):
        refs = []
        for s in sources:
            refs.append(f"[{s.id}] {s.title}. {s.url} (Credibility {int(s.credibility_score*100)}%)")
        return {"references": refs}

class PDFGeneratorAgent(Agent):
    async def run(self, html_path):
        pdf_path = html_path.with_suffix(".pdf")
        HTML(filename=str(html_path)).write_pdf(str(pdf_path))
        return {"pdf": pdf_path}

class AuditExporterAgent(Agent):
    async def run(self, audit_data):
        path = OUTPUT_DIR / f"audit_{uuid.uuid4().hex}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(audit_data, f, indent=2)
        return {"audit_path": path}

# =====================
# Orchestrator
# =====================

class Orchestrator:
    def __init__(self):
        self.topic = TopicAnalyzerAgent("Topic")
        self.planner = ResearchPlannerAgent("Planner")
        self.search = SearchAgent("Search")
        self.validator = SourceValidatorAgent("Validator")
        self.kb = KnowledgeBaseBuilderAgent("KB")
        self.writer = WriterAgent("Writer")
        self.critic = CriticAgent("Critic")
        self.refiner = RefinerAgent("Refiner")
        self.citation = CitationManagerAgent("Citation")
        self.pdf = PDFGeneratorAgent("PDF")
        self.audit = AuditExporterAgent("Audit")

    async def run(self, metadata: ReportMetadata):

        audit_log = {}

        t = await self.topic.run(metadata)
        audit_log["topic"] = t

        plan = await self.planner.run(t["topic"])
        audit_log["plan"] = plan

        search = await self.search.run(plan["queries"])
        audit_log["search"] = search

        valid = await self.validator.run(search["raw_results"])
        audit_log["sources"] = [asdict(s) for s in valid["sources"]]

        kb = await self.kb.run(valid["sources"])
        audit_log["kb"] = kb

        draft = await self.writer.run(kb, metadata)
        audit_log["draft"] = draft

        critic = await self.critic.run(draft["draft_v1"])
        audit_log["critic"] = critic

        refined = await self.refiner.run(draft["draft_v1"], critic["critic_notes"])
        audit_log["final"] = refined

        citations = await self.citation.run(valid["sources"])
        audit_log["citations"] = citations

        html_path = OUTPUT_DIR / f"report_{uuid.uuid4().hex}.html"

        html_content = self.render_html(metadata, refined["final_text"], citations["references"])
        html_path.write_text(html_content, encoding="utf-8")

        pdf = await self.pdf.run(html_path)

        audit_file = await self.audit.run(audit_log)

        return {
            "html": html_path,
            "pdf": pdf["pdf"]
        }, audit_file["audit_path"]

    def render_html(self, metadata, content, references):

        template = Template("""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{{ metadata.topic }}</title></head>
<body>
<h1>{{ metadata.topic }}</h1>
<p><b>Subject:</b> {{ metadata.subject }}</p>
<p><b>Researcher:</b> {{ metadata.researcher }}</p>
<p><b>Institution:</b> {{ metadata.institution }}</p>
<p><b>Date:</b> {{ metadata.date }}</p>
<hr>
<pre>{{ content }}</pre>
<hr>
<h2>References</h2>
{% for r in references %}
<p>{{ r }}</p>
{% endfor %}
</body>
</html>
""")

        return template.render(metadata=metadata, content=content, references=references)

# =====================
# Streamlit UI
# =====================

st.title("Online Report Writer – Enterprise Edition")

topic = st.text_input("Topic")
subject = st.text_input("Subject")
researcher = st.text_input("Researcher Name")
institution = st.text_input("Institution")
date = st.date_input("Date")

if st.button("Generate Report"):

    metadata = ReportMetadata(
        topic=topic,
        subject=subject,
        researcher=researcher,
        institution=institution,
        date=str(date)
    )

    with st.spinner("Generating report..."):
        orchestrator = Orchestrator()
        result, audit_path = asyncio.run(orchestrator.run(metadata))

    st.success("Report generated successfully")

    with open(result["html"], "r", encoding="utf-8") as f:
        st.download_button("Download HTML", f.read(), "report.html")

    with open(result["pdf"], "rb") as f:
        st.download_button("Download PDF", f.read(), "report.pdf")

    with open(audit_path, "r", encoding="utf-8") as f:
        st.download_button("Download Audit Log", f.read(), "audit.json")