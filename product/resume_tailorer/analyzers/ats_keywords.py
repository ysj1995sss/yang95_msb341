"""Which of a posting's key terms already appear on the resume, and which don't.

This is a presence check for the Jobs page, not a score: Candidate Fit stays
the only fit measure. Terms come from a curated vocabulary of phrases that
applicant-tracking systems commonly screen for, matched as whole words or
phrases (so "Go" never matches inside "go-to-market"). Missing terms are shown
to the user; they are never added to a resume unless the user's own verified
facts support them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

# Lowercase canonical term -> display label. Aliases map several spellings to one term.
VOCABULARY: dict[str, str] = {
    # Marketing and growth
    "product marketing": "Product marketing", "go-to-market": "Go-to-market", "gtm": "Go-to-market",
    "positioning": "Positioning", "messaging": "Messaging", "market research": "Market research",
    "competitive analysis": "Competitive analysis", "competitive intelligence": "Competitive intelligence",
    "customer segmentation": "Customer segmentation", "segmentation": "Segmentation",
    "demand generation": "Demand generation", "lead generation": "Lead generation",
    "lifecycle marketing": "Lifecycle marketing", "growth marketing": "Growth marketing",
    "brand strategy": "Brand strategy", "brand marketing": "Brand marketing", "content strategy": "Content strategy",
    "content marketing": "Content marketing", "email marketing": "Email marketing", "seo": "SEO", "sem": "SEM",
    "paid media": "Paid media", "paid search": "Paid search", "performance marketing": "Performance marketing",
    "social media": "Social media", "campaign management": "Campaign management", "product launch": "Product launch",
    "launches": "Product launch", "sales enablement": "Sales enablement", "customer journey": "Customer journey",
    "customer insights": "Customer insights", "pricing": "Pricing", "partner marketing": "Partner marketing",
    "field marketing": "Field marketing", "storytelling": "Storytelling", "copywriting": "Copywriting",
    "b2b": "B2B", "b2c": "B2C", "saas": "SaaS", "ecommerce": "E-commerce", "e-commerce": "E-commerce",
    # Product and strategy
    "product management": "Product management", "product strategy": "Product strategy", "roadmap": "Roadmap",
    "roadmapping": "Roadmap", "user research": "User research", "requirements gathering": "Requirements gathering",
    "agile": "Agile", "scrum": "Scrum", "okrs": "OKRs", "kpis": "KPIs", "a/b testing": "A/B testing",
    "experimentation": "Experimentation", "business strategy": "Business strategy", "strategic planning": "Strategic planning",
    "business development": "Business development", "partnerships": "Partnerships", "p&l": "P&L",
    "forecasting": "Forecasting", "financial modeling": "Financial modeling", "budgeting": "Budgeting",
    "market sizing": "Market sizing", "business case": "Business case", "consulting": "Consulting",
    # Working with people
    "stakeholder management": "Stakeholder management", "cross-functional": "Cross-functional collaboration",
    "project management": "Project management", "program management": "Program management",
    "change management": "Change management", "executive communication": "Executive communication",
    "presentation": "Presentations", "presentations": "Presentations", "negotiation": "Negotiation",
    "people management": "People management", "team leadership": "Team leadership", "mentoring": "Mentoring",
    "customer success": "Customer success", "account management": "Account management",
    # Analytics and operations
    "data analysis": "Data analysis", "analytics": "Analytics", "dashboards": "Dashboards", "reporting": "Reporting",
    "sql": "SQL", "excel": "Excel", "tableau": "Tableau", "power bi": "Power BI", "looker": "Looker",
    "google analytics": "Google Analytics", "python": "Python", "r": "R", "statistics": "Statistics",
    "machine learning": "Machine learning", "operations": "Operations", "supply chain": "Supply chain",
    "process improvement": "Process improvement", "logistics": "Logistics", "vendor management": "Vendor management",
    "salesforce": "Salesforce", "hubspot": "HubSpot", "marketo": "Marketo", "crm": "CRM", "jira": "Jira",
    "figma": "Figma", "powerpoint": "PowerPoint",
    # Engineering (kept short; the job analyzer covers more)
    "javascript": "JavaScript", "typescript": "TypeScript", "react": "React", "aws": "AWS", "api": "APIs",
    "apis": "APIs", "kubernetes": "Kubernetes", "docker": "Docker", "golang": "Go",
    # Credentials
    "mba": "MBA", "pmp": "PMP", "cpa": "CPA",
    # --- Spec 011: more fields, their tools and credentials, and common spelling variants ---
    # Data and software
    "postgresql": "PostgreSQL", "postgres": "PostgreSQL", "mysql": "MySQL", "sql server": "SQL Server",
    "mssql": "SQL Server", "oracle": "Oracle", "mongodb": "MongoDB", "snowflake": "Snowflake",
    "bigquery": "BigQuery", "redshift": "Redshift", "databricks": "Databricks", "dbt": "dbt",
    "airflow": "Airflow", "apache airflow": "Airflow", "spark": "Spark", "apache spark": "Spark",
    "pyspark": "Spark", "kafka": "Kafka", "hadoop": "Hadoop", "etl": "ETL", "elt": "ETL",
    "data pipelines": "Data pipelines", "data pipeline": "Data pipelines", "data modeling": "Data modeling",
    "data warehouse": "Data warehousing", "data warehousing": "Data warehousing", "pandas": "pandas",
    "numpy": "NumPy", "scikit-learn": "scikit-learn", "sklearn": "scikit-learn", "tensorflow": "TensorFlow",
    "pytorch": "PyTorch", "deep learning": "Deep learning", "nlp": "NLP", "natural language processing": "NLP",
    "powerbi": "Power BI", "microsoft power bi": "Power BI", "ms excel": "Excel", "microsoft excel": "Excel",
    "advanced excel": "Excel", "vba": "VBA", "sas": "SAS", "spss": "SPSS", "stata": "Stata", "alteryx": "Alteryx",
    "java": "Java", "c#": "C#", "c++": "C++", "ruby": "Ruby", "php": "PHP", "scala": "Scala", 
    "kotlin": "Kotlin", "js": "JavaScript", "node.js": "Node.js", "nodejs": "Node.js",
    "angular": "Angular", "vue": "Vue", "django": "Django", "flask": "Flask", "spring boot": "Spring Boot",
    ".net": ".NET", "graphql": "GraphQL", "rest apis": "REST APIs", "microservices": "Microservices",
    "amazon web services": "AWS", "azure": "Azure", "microsoft azure": "Azure", "gcp": "Google Cloud",
    "google cloud": "Google Cloud", "google cloud platform": "Google Cloud", "terraform": "Terraform",
    "ci/cd": "CI/CD", "jenkins": "Jenkins", "github actions": "GitHub Actions", "git": "Git", "linux": "Linux",
    "unit testing": "Unit testing", "test automation": "Test automation", "selenium": "Selenium",
    "devops": "DevOps", "sre": "SRE", "site reliability": "SRE", "cybersecurity": "Cybersecurity",
    "information security": "Cybersecurity", "siem": "SIEM", "soc 2": "SOC 2", "iso 27001": "ISO 27001",
    "aws certified": "AWS certification", "cissp": "CISSP", "security+": "Security+", "comptia": "CompTIA",
    # Finance and accounting
    "gaap": "GAAP", "ifrs": "IFRS", "financial reporting": "Financial reporting", "financial analysis": "Financial analysis",
    "fp&a": "FP&A", "financial planning and analysis": "FP&A", "variance analysis": "Variance analysis",
    "month-end close": "Month-end close", "month end close": "Month-end close", "reconciliation": "Reconciliations",
    "reconciliations": "Reconciliations", "accounts payable": "Accounts payable", "accounts receivable": "Accounts receivable",
    "general ledger": "General ledger", "audit": "Audit", "auditing": "Audit", "sox": "SOX", "tax": "Tax",
    "valuation": "Valuation", "dcf": "DCF", "netsuite": "NetSuite", "sap": "SAP", "quickbooks": "QuickBooks",
    "hyperion": "Hyperion", "bloomberg": "Bloomberg", "cfa": "CFA", "cma": "CMA", "cia": "CIA", "frm": "FRM",
    "series 7": "Series 7", "series 63": "Series 63",
    # Healthcare and nursing
    "registered nurse": "RN", "rn": "RN", "lpn": "LPN", "bsn": "BSN", "msn": "MSN", "np": "Nurse practitioner",
    "nurse practitioner": "Nurse practitioner", "bls": "BLS", "basic life support": "BLS", "acls": "ACLS",
    "pals": "PALS", "cna": "CNA", "epic": "Epic", "cerner": "Cerner", "ehr": "EHR", "electronic health record": "EHR",
    "electronic health records": "EHR", "emr": "EHR", "hipaa": "HIPAA", "patient care": "Patient care",
    "acute care": "Acute care", "med/surg": "Med/surg", "medical-surgical": "Med/surg", "icu": "ICU",
    "medication administration": "Medication administration", "triage": "Triage", "case management": "Case management",
    "clinical documentation": "Clinical documentation", "icd-10": "ICD-10", "medical coding": "Medical coding",
    # Operations, supply chain and manufacturing
    "six sigma": "Six Sigma", "lean six sigma": "Lean Six Sigma", "kaizen": "Kaizen",
    "inventory management": "Inventory management", "procurement": "Procurement", "sourcing": "Sourcing",
    "demand planning": "Demand planning", "s&op": "S&OP", "erp": "ERP", "warehouse management": "Warehouse management",
    "quality assurance": "Quality assurance", "quality control": "Quality control", "osha": "OSHA",
    "cad": "CAD", "autocad": "AutoCAD", "solidworks": "SolidWorks", "plc": "PLC", "gd&t": "GD&T",
    "pe license": "PE license", "professional engineer": "PE license", "cscp": "CSCP", "cpim": "CPIM",
    # Sales and customer
    "b2b sales": "B2B sales", "saas sales": "SaaS sales", "quota": "Quota attainment", "pipeline management": "Pipeline management",
    "lead qualification": "Lead qualification", "prospecting": "Prospecting",
    "outbound": "Prospecting", "upselling": "Upselling", "renewals": "Renewals",
    "customer retention": "Customer retention", "zendesk": "Zendesk", "gong": "Gong", 
    # People, HR and education
    "recruiting": "Recruiting", "talent acquisition": "Recruiting", "onboarding": "Onboarding",
    "employee relations": "Employee relations", "compensation": "Compensation", "benefits administration": "Benefits administration",
    "hris": "HRIS", "workday": "Workday", "payroll": "Payroll", "shrm-cp": "SHRM-CP", "shrm-scp": "SHRM-SCP", "phr": "PHR",
    "curriculum development": "Curriculum development", "lesson planning": "Lesson planning",
    "classroom management": "Classroom management", "teaching license": "Teaching license",
    "instructional design": "Instructional design",
    # Design, product and legal
    "ux": "UX design", "ux design": "UX design", "ui design": "UI design", "user experience": "UX design",
    "wireframing": "Wireframing", "prototyping": "Prototyping", "adobe creative suite": "Adobe Creative Suite",
    "photoshop": "Photoshop", "illustrator": "Illustrator", "indesign": "InDesign", "sketch": "Sketch",
    "accessibility": "Accessibility", "wcag": "Accessibility", "contract negotiation": "Contract negotiation",
    "contracts": "Contracts", "compliance": "Compliance", "regulatory": "Regulatory compliance",
    "litigation": "Litigation", "bar admission": "Bar admission", "paralegal": "Paralegal",
    # Project and program credentials
    "capm": "CAPM", "csm": "Scrum Master certification", "scrum master": "Scrum Master certification",
    "itil": "ITIL", "prince2": "PRINCE2", "asana": "Asana", "smartsheet": "Smartsheet", "ms project": "MS Project",
    "microsoft project": "MS Project", "confluence": "Confluence", "tableau desktop": "Tableau", "looker studio": "Looker",
}

# Single letters and very short tokens need standalone context to count.
_AMBIGUOUS = {"r"}


@dataclass(frozen=True)
class KeywordCheck:
    present: tuple[str, ...]
    missing: tuple[str, ...]

    @property
    def summary(self) -> str:
        total = len(self.present) + len(self.missing)
        if total == 0:
            return "No common screening keywords were found in this posting."
        return f"{len(self.present)} of {total} posting terms appear in your Career Profile."


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower().replace("–", "-").replace("—", "-"))


def _pattern(term: str) -> re.Pattern:
    # Whole word/phrase; a neighbouring letter, digit or hyphen means it's part of something else.
    escaped = re.escape(term).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![\w-]){escaped}(?![\w-]|-\w)")


_PATTERNS = {term: _pattern(term) for term in VOCABULARY}


def terms_in(text: str) -> list[str]:
    """Display labels of vocabulary terms found in text, most frequent first."""
    norm = _normalize(text)
    counts: dict[str, int] = {}
    for term, label in VOCABULARY.items():
        if term in _AMBIGUOUS:
            hits = len(re.findall(rf"(?:^|[\s,(/]){re.escape(term)}(?=[\s,)/.;]|$)", norm))
        else:
            hits = len(_PATTERNS[term].findall(norm))
        if hits:
            counts[label] = counts.get(label, 0) + hits
    return sorted(counts, key=lambda label: (-counts[label], label))


# The facts a resume is built from. Contact details, goals and preferences aren't evidence of a
# skill, so they never count (spec 010).
FACT_FIELDS = ("summary", "work_experience", "education", "skills", "tools", "certifications", "accomplishments")


def profile_text(profile: Any) -> str:
    """The Career Profile's facts as text, for a presence check (not the resume itself)."""
    data = profile.to_dict() if hasattr(profile, "to_dict") else (profile or {})
    data = {key: data.get(key) for key in FACT_FIELDS if isinstance(data, dict)}
    parts: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)

    walk(data)
    return "\n".join(parts)


def check_keywords(posting: str, resume_text: str, limit: int = 20) -> KeywordCheck:
    """Key terms in the posting, split into found and not found in the given text."""
    wanted = terms_in(posting)[:limit]
    have = set(terms_in(resume_text))
    return KeywordCheck(
        present=tuple(t for t in wanted if t in have),
        missing=tuple(t for t in wanted if t not in have),
    )
