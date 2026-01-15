
import streamlit as st
import asyncio
import uuid
import json
import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict
import requests
from pathlib import Path

# ============================
# Configuration
# ============================

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

ALLOWED_DOMAINS = [".edu", ".gov", ".org", "ieee.org", "nature.com", "sciencedirect.com", "acm.org", "springer.com"]

LLM_MODEL = "gpt-4o-mini"  # or your preferred model
SEARCH_API_KEY = "YOUR_SEARCH_API_KEY"
OPENAI_API_KEY = "OPENAI_API_KEY"

# ============================
# Data Models
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
# Utility Functions
# ============================

def domain_allowed(url: str) -> bool:
    return any(domain in url.lower() for domain in ALLOWED_DOMAINS)

def save_json(data, filename):
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path

# ============================
# Base Agent
# ============================

class Agent:
    def __init__(self, name: str):
        self.name = name

    async def run(self, input_data):
        raise NotImplementedError

# ============================
# Agents
# ============================

class TopicAnalyzerAgent(Agent):
    async def run(self, topic: str):
        return {
            "main_topic": topic,
            "subtopics": ["technical advances", "statistics", "applications", "ethics", "industry adoption", "future trends"],
            "research_dimensions": ["technical", "statistical", "policy", "applications", "ethics", "future"],
            "keyword_clusters": {
                "technical": [topic, "deep learning", "transformers"],
                "statistics": [topic, "market size", "publications"],
                "policy": [topic, "regulation", "governance"]
            }
        }

class ResearchPlannerAgent(Agent):
    async def run(self, topic_analysis: Dict):
        queries = []
        base = topic_analysis["main_topic"]

        for dim in topic_analysis["research_dimensions"]:
            queries.append({"query": f"{base} {dim} site:edu", "category": dim})
            queries.append({"query": f"{base} {dim} site:gov", "category": dim})

        return {"queries": queries[:15]}

class SearchAgent(Agent):
    async def run(self, query_obj: Dict):
        # Placeholder: integrate SerpAPI / Bing API here
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
    async def run(self, raw_sources: List[Dict]):
        accepted = []
        rejected = []
        sid = 1

        for src in raw_sources:
            if domain_allowed(src["url"]):
                accepted.append(Source(
                    id=sid,
                    title=src["title"],
                    authors=["Unknown"],
                    year=2024,
                    publisher="Stanford",
                    journal="AI Index",
                    doi="",
                    url=src["url"],
                    credibility_score=0.95
                ))
                sid += 1
            else:
                rejected.append(src)

        return {"accepted_sources": accepted, "rejected_sources": rejected}

class KnowledgeBaseBuilderAgent(Agent):
    async def run(self, sources: List[Source]):
        facts = []
        for s in sources:
            facts.append({
                "claim": f"Information derived from {s.title}",
                "source_id": s.id,
                "confidence": s.credibility_score
            })
        return {"facts": facts}

class WriterAgent(Agent):
    async def run(self, kb: Dict, metadata: ReportMetadata):
        sections = {
            "abstract": "This report analyzes recent developments...",
            "introduction": f"This report explores {metadata.topic}.",
            "body": "Detailed technical and statistical discussion.",
            "conclusion": "Summary of findings."
        }
        return {"draft_v1": sections}

class CriticAgent(Agent):
    async def run(self, draft: Dict, kb: Dict):
        return {
            "issues": [],
            "recommendations": ["Improve transitions", "Add more citations"]
        }

class RefinerAgent(Agent):
    async def run(self, draft: Dict, critic_report: Dict):
        refined = draft.copy()
        refined["executive_summary"] = "Executive summary added."
        return {"final_text": refined}

class CitationManagerAgent(Agent):
    async def run(self, final_text: Dict, sources: List[Source]):
        references = []
        for s in sources:
            references.append(f"[{s.id}] {s.title}. {s.publisher}, {s.year}. {s.url}")
        return {"references": references}

class PDFGeneratorAgent(Agent):
    async def run(self, final_text: Dict, references: List[str], metadata: ReportMetadata):
        html = f"""
        <html><body>
        <h1>{metadata.topic}</h1>
        <h3>{metadata.researcher} - {metadata.institution}</h3>
        <p>{metadata.date}</p>
        <hr/>
        """

        for k, v in final_text.items():
            html += f"<h2>{k}</h2><p>{v}</p>"

        html += "<h2>References</h2>"
        for r in references:
            html += f"<p>{r}</p>"

        html += "</body></html>"

        html_path = OUTPUT_DIR / "report.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        return {"html_path": str(html_path)}

class AuditExporterAgent(Agent):
    async def run(self, audit_data: Dict):
        return save_json(audit_data, "audit.json")

# ============================
# Orchestrator
# ============================

class Orchestrator:

    def __init__(self):
        self.topic_agent = TopicAnalyzerAgent("TopicAnalyzer")
        self.planner_agent = ResearchPlannerAgent("Planner")
        self.search_agent = SearchAgent("Searcher")
        self.validator_agent = SourceValidatorAgent("Validator")
        self.kb_agent = KnowledgeBaseBuilderAgent("KB")
        self.writer_agent = WriterAgent("Writer")
        self.critic_agent = CriticAgent("Critic")
        self.refiner_agent = RefinerAgent("Refiner")
        self.citation_agent = CitationManagerAgent("Citation")
        self.pdf_agent = PDFGeneratorAgent("PDF")
        self.audit_agent = AuditExporterAgent("Audit")

    async def run(self, metadata: ReportMetadata):

        topic_analysis = await self.topic_agent.run(metadata.topic)
        plan = await self.planner_agent.run(topic_analysis)

        raw_sources = []
        for q in plan["queries"]:
            result = await self.search_agent.run(q)
            raw_sources.extend(result["raw_results"])

        validation = await self.validator_agent.run(raw_sources)
        sources = validation["accepted_sources"]

        kb = await self.kb_agent.run(sources)
        draft = await self.writer_agent.run(kb, metadata)
        critic = await self.critic_agent.run(draft, kb)
        refined = await self.refiner_agent.run(draft["draft_v1"], critic)
        citations = await self.citation_agent.run(refined["final_text"], sources)
        pdf_result = await self.pdf_agent.run(refined["final_text"], citations["references"], metadata)

        audit_data = {
            "metadata": asdict(metadata),
            "topic_analysis": topic_analysis,
            "queries": plan["queries"],
            "sources": [asdict(s) for s in sources],
            "critic_report": critic
        }

        audit_path = await self.audit_agent.run(audit_data)

        return pdf_result["html_path"], audit_path

# ============================
# Streamlit UI
# ============================

st.set_page_config(page_title="Online Report Writer", layout="wide")

st.title("📄 Online Report Writer (Multi-Agent System)")

topic = st.text_input("Report Topic")
subject = st.text_input("Subject / Field")
researcher = st.text_input("Researcher Name")
institution = st.text_input("Institution")
date = st.date_input("Date", datetime.date.today())

if st.button("Generate Report"):

    if not topic:
        st.error("Please enter a topic.")
    else:
        with st.spinner("Running multi-agent research pipeline..."):

            metadata = ReportMetadata(
                topic=topic,
                subject=subject,
                researcher=researcher,
                institution=institution,
                date=str(date)
            )

            orchestrator = Orchestrator()
            html_path, audit_path = asyncio.run(orchestrator.run(metadata))

            st.success("Report generated successfully!")

            with open(html_path, "r", encoding="utf-8") as f:
                st.download_button("Download HTML Report", f.read(), file_name="report.html")

            with open(audit_path, "r", encoding="utf-8") as f:
                st.download_button("Download Audit JSON", f.read(), file_name="audit.json")
