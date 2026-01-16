# streamlit_app.py – Enterprise Edition v1.0 (Cloud Compatible, OpenAI SDK v1+)

import os
import json
import asyncio
import uuid
import requests
from dataclasses import dataclass, asdict
from typing import List
from pathlib import Path
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import streamlit as st

from openai import OpenAI

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

# =====================
# Environment
# =====================

load_dotenv()

OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY")
BING_API_KEY = st.secrets.get("BING_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set")

client = OpenAI(api_key=OPENAI_API_KEY)

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

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
# Base Agent
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
            f"{topic} site:org",
        ]
        return {"queries": queries}

class SearchAgent(Agent):
    async def run(self, queries):
        headers = {"Ocp-Apim-Subscription-Key": BING_API_KEY}
        results = []

        for q in queries:
            try:
                url = "https://api.bing.microsoft.com/v7.0/search"
                params = {"q": q, "count": 5}
                r = requests.get(url, headers=headers, params=params, timeout=15)
                data = r.json()

                for item in data.get("webPages", {}).get("value", []):
                    results.append({
                        "title": item.get("name"),
                        "url": item.get("url"),
                        "domain": item.get("url").split("/")[2]
                    })
            except:
                continue

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
                html = requests.get(s.url, timeout=15).text
                soup = BeautifulSoup(html, "html.parser")
                text = " ".join(p.get_text() for p in soup.find_all("p")[:10])
                facts.append({
                    "source_id": s.id,
                    "text": text[:2000]
                })
            except:
                continue

        return {"facts": facts}

class WriterAgent(Agent):
    async def run(self, kb, metadata):

        prompt = f"""
Write a professional academic research report on:

Topic: {metadata.topic}

Use the following extracted factual material:

{json.dumps(kb["facts"], indent=2)}

Required sections:
Executive Summary
Abstract
Introduction
Literature Review
Main Analysis
Data & Statistics
Challenges
Future Outlook
Conclusion

Use in-text numeric citations like [1], [2].
"""

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=3500
        )

        return {"draft_v1": resp.choices[0].message.content}

class CriticAgent(Agent):
    async def run(self, draft):
        prompt = f"Review this report for factual errors, missing sections, structure, clarity:\n{draft}"

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1200
        )

        return {"critic_notes": resp.choices[0].message.content}

class RefinerAgent(Agent):
    async def run(self, draft, critic):

        prompt = f"""
Improve the report using the feedback below.

Feedback:
{critic}

Report:
{draft}

Return the improved final report.
"""

        resp = client.chat.completions.create(
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
            refs.append(f"[{s.id}] {s.title}. {s.url}")
        return {"references": refs}

class PDFGeneratorAgent(Agent):
    async def run(self, content_text, metadata):

        pdf_path = OUTPUT_DIR / f"report_{uuid.uuid4().hex}.pdf"
        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)

        story = []

        story.append(Paragraph(metadata.topic, styles["Title"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Subject: {metadata.subject}", styles["Normal"]))
        story.append(Paragraph(f"Researcher: {metadata.researcher}", styles["Normal"]))
        story.append(Paragraph(f"Institution: {metadata.institution}", styles["Normal"]))
        story.append(Paragraph(f"Date: {metadata.date}", styles["Normal"]))
        story.append(PageBreak())

        for block in content_text.split("\n\n"):
            safe = block.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(safe, styles["BodyText"]))
            story.append(Spacer(1, 10))

        doc.build(story)

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
        plan = await self.planner.run(t["topic"])
        search = await self.search.run(plan["queries"])
        valid = await self.validator.run(search["raw_results"])
        kb = await self.kb.run(valid["sources"])
        draft = await self.writer.run(kb, metadata)
        critic = await self.critic.run(draft["draft_v1"])
        refined = await self.refiner.run(draft["draft_v1"], critic["critic_notes"])
        citations = await self.citation.run(valid["sources"])

        audit_log.update({
            "topic": t,
            "queries": plan,
            "sources": [asdict(s) for s in valid["sources"]],
            "kb": kb,
            "draft": draft,
            "critic": critic,
            "final": refined,
            "citations": citations
        })

        pdf = await self.pdf.run(refined["final_text"], metadata)
        audit_file = await self.audit.run(audit_log)

        return pdf["pdf"], audit_file["audit_path"]

# =====================
# Streamlit UI
# =====================

st.set_page_config(page_title="Online Report Writer – Enterprise Edition")

st.title("Online Report Writer – Enterprise Edition")

topic = st.text_input("Topic")
subject = st.text_input("Subject")
researcher = st.text_input("Researcher Name")
institution = st.text_input("Institution")
date = st.date_input("Date")

if st.button("Generate Report"):

    if not topic or not subject or not researcher or not institution:
        st.error("Please complete all fields.")
    else:
        metadata = ReportMetadata(
            topic=topic,
            subject=subject,
            researcher=researcher,
            institution=institution,
            date=str(date)
        )

        with st.spinner("Running multi-agent research and report generation..."):
            orchestrator = Orchestrator()
            pdf_path, audit_path = asyncio.run(orchestrator.run(metadata))

        st.success("Report generated successfully.")

        with open(pdf_path, "rb") as f:
            st.download_button("Download PDF Report", f.read(), "report.pdf")

        with open(audit_path, "r", encoding="utf-8") as f:
            st.download_button("Download Audit Log", f.read(), "audit.json")