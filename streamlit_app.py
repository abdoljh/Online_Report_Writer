# Streamlit app.py
# v2.0
# ChatGPT
# Jan. 15, 2026

import os
import json
import asyncio
import uuid
import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict
from pathlib import Path
from dotenv import load_dotenv

import streamlit as st
import httpx
from jinja2 import Environment, FileSystemLoader

# ============================
# ENVIRONMENT
# ============================

load_dotenv()

#OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
#SEARCH_API_KEY = os.getenv("SEARCH_API_KEY")
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "serpapi")
PDF_ENGINE = os.getenv("PDF_ENGINE", "weasyprint")

# Get API key from Streamlit secrets
# Access secrets safely
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY")
SEARCH_API_KEY = st.secrets.get("SEARCH_API_KEY")

# Check if they exist
if not OPENAI_API_KEY or not SEARCH_API_KEY:
    st.error("Missing API keys in Streamlit Secrets!")
    raise RuntimeError("Missing API keys. Check Streamlit Secrets.")

# ============================
# PATHS
# ============================

#BASE_DIR = Path(__file__).parent
#OUTPUT_DIR = BASE_DIR / "outputs"
#TEMPLATE_DIR = BASE_DIR / "templates"

#OUTPUT_DIR.mkdir(exist_ok=True)


# Define your base directory (the folder where your script lives)
BASE_DIR = Path(__file__).resolve().parent

# Define subdirectories
OUTPUT_DIR = BASE_DIR / "outputs"
TEMPLATE_DIR = BASE_DIR / "templates"

# Ensure the directories exist (prevents FileNotFoundError)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)


# ============================
# CONFIG
# ============================

ALLOWED_DOMAINS = [
    ".edu", ".gov", ".org",
    "ieee.org", "nature.com", "sciencedirect.com",
    "acm.org", "springer.com", "nih.gov", "who.int"
]

# ============================
# DATA MODELS
# ============================

@dataclass
class Source:
    id: int
    title: str
    authors: List[str]
    year: int
    publisher: str
    journal: str
    doi: str
    url: str
    credibility_score: float

@dataclass
class ReportMetadata:
    topic: str
    subject: str
    researcher: str
    institution: str
    date: str

# ============================
# UTILITIES
# ============================

def domain_allowed(url: str) -> bool:
    return any(d in url.lower() for d in ALLOWED_DOMAINS)

def save_json(data, filename):
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path

# ============================
# BASE AGENT
# ============================

class Agent:
    def __init__(self, name: str):
        self.name = name

    async def run(self, *args, **kwargs):
        raise NotImplementedError

# ============================
# AGENTS
# ============================

class TopicAnalyzerAgent(Agent):
    async def run(self, topic):
        return {
            "main_topic": topic,
            "subtopics": [
                "technical advances",
                "statistics",
                "industry adoption",
                "ethics and governance",
                "policy",
                "future outlook"
            ],
            "research_dimensions": [
                "technical", "statistical", "industry",
                "ethics", "policy", "future"
            ]
        }

class ResearchPlannerAgent(Agent):
    async def run(self, topic_analysis):
        base = topic_analysis["main_topic"]
        queries = []

        for dim in topic_analysis["research_dimensions"]:
            queries.append({"query": f"{base} {dim} site:edu", "category": dim})
            queries.append({"query": f"{base} {dim} site:gov", "category": dim})

        return {"queries": queries[:15]}

class SearchAgent(Agent):
    async def run(self, query_obj):
        # Placeholder for SerpAPI / Bing integration
        await asyncio.sleep(0.1)

        return {
            "raw_results": [
                {
                    "url": "https://hai.stanford.edu/ai-index",
                    "title": "AI Index Report",
                    "snippet": "Annual AI trends report",
                    "domain": "hai.stanford.edu"
                }
            ]
        }

class SourceValidatorAgent(Agent):
    async def run(self, raw_sources):
        accepted = []
        rejected = []
        sid = 1

        seen_urls = set()

        for src in raw_sources:
            url = src["url"]

            if url in seen_urls:
                continue
            seen_urls.add(url)

            if domain_allowed(url):
                accepted.append(Source(
                    id=sid,
                    title=src["title"],
                    authors=["Unknown"],
                    year=2024,
                    publisher="Stanford",
                    journal="AI Index",
                    doi="",
                    url=url,
                    credibility_score=0.95
                ))
                sid += 1
            else:
                rejected.append(src)

        return {"accepted_sources": accepted, "rejected_sources": rejected}

class KnowledgeBaseBuilderAgent(Agent):
    async def run(self, sources):
        facts = []
        for s in sources:
            facts.append({
                "claim": f"Derived insight from {s.title}",
                "source_id": s.id,
                "confidence": s.credibility_score
            })
        return {"facts": facts}

class WriterAgent(Agent):
    async def run(self, kb, metadata):
        return {
            "draft_v1": {
                "abstract": f"This report analyzes {metadata.topic}.",
                "introduction": f"{metadata.topic} is a rapidly evolving field.",
                "analysis": "Detailed technical and statistical analysis.",
                "conclusion": "Summary of findings."
            }
        }

class CriticAgent(Agent):
    async def run(self, draft, kb):
        return {
            "issues": [],
            "recommendations": ["Expand statistical justification"]
        }

class RefinerAgent(Agent):
    async def run(self, draft, critic):
        refined = dict(draft)
        refined["executive_summary"] = "This report summarizes major findings."
        return {"final_text": refined}

class CitationManagerAgent(Agent):
    async def run(self, final_text, sources):
        refs = []
        for s in sources:
            refs.append(f"[{s.id}] {s.title}. {s.publisher}, {s.year}. {s.url}")
        return {"references": refs}

class PDFGeneratorAgent(Agent):
    async def run(self, final_text, references, metadata):
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("report_template.html")

        html = template.render(
            metadata=metadata,
            content=final_text,
            references=references
        )

        html_path = OUTPUT_DIR / "report.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        pdf_path = None

        if PDF_ENGINE == "weasyprint":
            try:
                from weasyprint import HTML
                pdf_path = OUTPUT_DIR / "report.pdf"
                HTML(string=html).write_pdf(pdf_path)
            except Exception as e:
                print("PDF generation failed:", e)

        return {"html": html_path, "pdf": pdf_path}

class AuditExporterAgent(Agent):
    async def run(self, audit_data):
        return save_json(audit_data, "audit.json")

# ============================
# ORCHESTRATOR
# ============================

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

    async def run(self, metadata):

        topic_analysis = await self.topic.run(metadata.topic)
        plan = await self.planner.run(topic_analysis)

        search_tasks = [self.search.run(q) for q in plan["queries"]]
        search_results = await asyncio.gather(*search_tasks)

        raw_sources = []
        for r in search_results:
            raw_sources.extend(r["raw_results"])

        validation = await self.validator.run(raw_sources)
        sources = validation["accepted_sources"]

        kb = await self.kb.run(sources)
        draft = await self.writer.run(kb, metadata)
        critic = await self.critic.run(draft, kb)
        refined = await self.refiner.run(draft["draft_v1"], critic)
        citations = await self.citation.run(refined["final_text"], sources)
        pdf_result = await self.pdf.run(refined["final_text"], citations["references"], metadata)

        audit_data = {
            "metadata": asdict(metadata),
            "topic_analysis": topic_analysis,
            "queries": plan["queries"],
            "sources": [asdict(s) for s in sources],
            "critic_report": critic
        }

        audit_path = await self.audit.run(audit_data)

        return pdf_result, audit_path

# ============================
# STREAMLIT UI
# ============================

st.set_page_config(page_title="Online Report Writer – Enterprise", layout="wide")
st.title("Online Report Writer – Enterprise Edition")

topic = st.text_input("Report Topic")
subject = st.text_input("Subject")
researcher = st.text_input("Researcher Name")
institution = st.text_input("Institution")
date = st.date_input("Date", datetime.date.today())

if st.button("Generate Report"):

    if not topic:
        st.error("Topic is required.")
    else:
        with st.spinner("Running enterprise multi-agent pipeline..."):

            metadata = ReportMetadata(
                topic=topic,
                subject=subject,
                researcher=researcher,
                institution=institution,
                date=str(date)
            )

            orchestrator = Orchestrator()
            result, audit_path = asyncio.run(orchestrator.run(metadata))

            st.success("Report generated successfully.")

            if result["html"]:
                with open(result["html"], "r", encoding="utf-8") as f:
                    st.download_button("Download HTML", f.read(), "report.html")

            if result["pdf"] and result["pdf"].exists():
                with open(result["pdf"], "rb") as f:
                    st.download_button("Download PDF", f.read(), "report.pdf")

            with open(audit_path, "r", encoding="utf-8") as f:
                st.download_button("Download Audit JSON", f.read(), "audit.json")