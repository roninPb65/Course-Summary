import os
import re
import json
import time
import datetime
from flask import Flask, render_template, request, Response, stream_with_context
from tavily import TavilyClient

app = Flask(__name__)

# ── All 26 Alberta post-secondary institutions ──────────────────────────────
UNIVERSITIES = [
    "auarts.ca", "ambrose.edu", "athabascau.ca", "concordia.ab.ca",
    "macewan.ca", "mtroyal.ca", "stmarys.ab.ca", "kingsu.ca",
    "ualberta.ca", "ucalgary.ca", "ulethbridge.ca",
]
COLLEGES = [
    "banffcentre.ca", "bowvalleycollege.ca", "burmanu.ca", "keyano.ca",
    "lakelandcollege.ca", "lethbridgecollege.ca", "mhc.ab.ca", "nait.ca",
    "norquest.ca", "northernlakescollege.ca", "nwpolytech.ca",
    "oldscollege.ca", "portage.ab.ca", "reddeer.ca", "sait.ca",
]
INSTITUTION_NAMES = {
    "auarts.ca":               "Alberta University of the Arts",
    "ambrose.edu":             "Ambrose University",
    "athabascau.ca":           "Athabasca University",
    "concordia.ab.ca":         "Concordia University of Edmonton",
    "macewan.ca":              "MacEwan University",
    "mtroyal.ca":              "Mount Royal University",
    "stmarys.ab.ca":           "St. Mary's University",
    "kingsu.ca":               "The King's University",
    "ualberta.ca":             "University of Alberta",
    "ucalgary.ca":             "University of Calgary",
    "ulethbridge.ca":          "University of Lethbridge",
    "banffcentre.ca":          "Banff Centre for Arts & Creativity",
    "bowvalleycollege.ca":     "Bow Valley College",
    "burmanu.ca":              "Burman University",
    "keyano.ca":               "Keyano College",
    "lakelandcollege.ca":      "Lakeland College",
    "lethbridgecollege.ca":    "Lethbridge College",
    "mhc.ab.ca":               "Medicine Hat College",
    "nait.ca":                 "NAIT",
    "norquest.ca":             "NorQuest College",
    "northernlakescollege.ca": "Northern Lakes College",
    "nwpolytech.ca":           "Northwestern Polytechnic",
    "oldscollege.ca":          "Olds College",
    "portage.ab.ca":           "Portage College",
    "reddeer.ca":              "Red Deer Polytechnic",
    "sait.ca":                 "SAIT",
}
INSTITUTION_TYPE = {d: "university" for d in UNIVERSITIES}
INSTITUTION_TYPE.update({d: "college" for d in COLLEGES})

# ── Career → academic program term mapping ─────────────────────────────────
CAREER_TERM_MAP = {
    "software developer":      ["software development", "computer systems technology", "computing science", "software engineering technology"],
    "software engineer":       ["software engineering", "computing science", "computer engineering", "software development"],
    "web developer":           ["web development", "internet communications technology", "digital media", "web design and development"],
    "data scientist":          ["data analytics", "data science", "statistics", "machine learning", "business intelligence"],
    "cybersecurity":           ["cybersecurity", "information security", "network security", "information systems security"],
    "network administrator":   ["computer networking", "network administration", "IT systems", "information technology"],
    "game developer":          ["game development", "interactive digital media", "3D animation", "digital arts"],
    "ai developer":            ["artificial intelligence", "machine learning", "data science", "computing science"],
    "database administrator":  ["database administration", "information technology", "computer systems", "data management"],
    "nurse":                   ["nursing", "practical nurse", "BScN bachelor of science nursing", "registered nurse"],
    "registered nurse":        ["BScN nursing", "bachelor of science nursing", "registered nurse program"],
    "practical nurse":         ["practical nurse diploma", "PN program", "licensed practical nurse"],
    "doctor":                  ["pre-medicine", "pre-med biology", "health sciences", "biomedical sciences"],
    "pharmacist":              ["pharmacy", "pharmaceutical sciences", "pharmacology"],
    "paramedic":               ["paramedic", "emergency medical services", "EMS", "paramedicine"],
    "physiotherapist":         ["physical therapy", "kinesiology", "physiotherapy", "rehabilitation sciences"],
    "dental hygienist":        ["dental hygiene", "dental assistant", "oral health"],
    "medical lab":             ["medical laboratory technology", "medical laboratory science", "MLT"],
    "radiologist":             ["medical radiologic technology", "diagnostic imaging", "radiography"],
    "health care aide":        ["health care aide", "continuing care assistant", "personal support worker"],
    "engineer":                ["engineering", "engineering technology", "applied science"],
    "civil engineer":          ["civil engineering", "civil engineering technology", "structural engineering"],
    "mechanical engineer":     ["mechanical engineering", "mechanical engineering technology", "mechatronics"],
    "electrical engineer":     ["electrical engineering", "electrical engineering technology", "power engineering"],
    "petroleum engineer":      ["petroleum engineering", "oil and gas", "chemical engineering", "energy"],
    "environmental engineer":  ["environmental engineering", "environmental technology", "environmental science"],
    "chemical engineer":       ["chemical engineering", "chemical technology", "process engineering"],
    "electrician":             ["electrical apprenticeship", "electrical technology", "industrial electrician", "power engineering"],
    "plumber":                 ["plumbing apprenticeship", "plumber journeyman", "pipefitting"],
    "welder":                  ["welding", "welding fabrication", "metal fabrication", "welding technology"],
    "carpenter":               ["carpentry", "construction", "building construction technology"],
    "hvac":                    ["HVAC", "refrigeration and air conditioning", "building systems"],
    "mechanic":                ["automotive service technology", "auto mechanic", "heavy equipment technology"],
    "accountant":              ["accounting", "CPA", "bachelor of commerce", "financial management"],
    "business analyst":        ["business analysis", "management information systems", "business administration"],
    "marketing":               ["marketing", "digital marketing", "advertising", "business marketing"],
    "human resources":         ["human resources management", "HR management", "HRM"],
    "graphic designer":        ["graphic design", "graphic communications", "visual communications"],
    "ux designer":             ["UX design", "user experience design", "interaction design"],
    "animator":                ["animation", "3D animation", "motion graphics", "digital media arts"],
    "teacher":                 ["education", "bachelor of education", "BEd", "teaching certificate"],
    "early childhood":         ["early childhood education", "ECE", "child and youth care"],
    "social worker":           ["social work", "BSW bachelor of social work", "social sciences"],
    "psychologist":            ["psychology", "counselling", "mental health", "applied psychology"],
    "environmental scientist": ["environmental science", "ecology", "environmental studies", "natural resources"],
    "biologist":               ["biology", "biological sciences", "life sciences", "ecology"],
    "agriculturalist":         ["agriculture", "agribusiness", "agronomy", "animal science"],
    "veterinarian":            ["veterinary technology", "animal health technology"],
    "chef":                    ["culinary arts", "baking and pastry arts", "cook apprenticeship"],
    "hotel manager":           ["hospitality management", "hotel management", "tourism management"],
    "police officer":          ["police studies", "law enforcement", "justice studies", "criminal justice"],
    "pilot":                   ["aviation", "flight training", "commercial pilot", "aeronautical"],
    "logistics":               ["supply chain management", "logistics", "transportation management"],
    "filmmaker":               ["film production", "digital video", "film studies", "media production"],
    "architect":               ["architecture", "architectural technology", "architectural design"],
    "interior designer":       ["interior design", "interior decorating", "architectural technology"],
    "photographer":            ["photography", "photographic arts", "visual arts", "media arts"],
}


def get_client() -> TavilyClient:
    key = os.environ.get("TAVILY_API_KEY", "")
    if not key:
        raise ValueError("TAVILY_API_KEY is not set. Add it to your .env file or Render dashboard.")
    return TavilyClient(api_key=key)


def career_to_terms(career: str) -> list[str]:
    career_lower = career.lower().strip()
    if career_lower in CAREER_TERM_MAP:
        return CAREER_TERM_MAP[career_lower]
    for key, terms in CAREER_TERM_MAP.items():
        if key in career_lower or career_lower in key:
            return terms
    words = career_lower.split()
    for key, terms in CAREER_TERM_MAP.items():
        if any(w in key for w in words if len(w) > 3):
            return terms
    return [career, f"{career} program", f"{career} technology", f"{career} diploma", f"bachelor of {career}"]


def _is_program_page(url: str, title: str) -> bool:
    url_lower, title_lower = url.lower(), title.lower()
    skip = ["/news", "/events", "/about", "/contact", "/faculty", "/research",
            "/campus", "/student-services", "/jobs", "/library", "/athletics", "login"]
    if any(p in url_lower for p in skip):
        return False
    good_url  = ["program", "course", "diploma", "certificate", "degree", "bachelor", "major", "credential", "study"]
    good_title = ["diploma", "certificate", "degree", "bachelor", "program", "technology", "technician",
                  "science", "engineering", "management", "arts", "design", "nursing", "education", "apprenticeship"]
    return any(s in url_lower for s in good_url) or any(w in title_lower for w in good_title)


def _parse_result(r: dict, matched_term: str = "", search_query: str = "") -> dict | None:
    url     = (r.get("url") or "").strip()
    title   = (r.get("title") or "").strip()
    content = (r.get("content") or "").strip()
    score   = r.get("score", 0)

    if not title or len(content) < 30:
        return None
    if not _is_program_page(url, title):
        return None

    # Strip institution suffix from title
    title = re.sub(r'\s*[|\-–—]\s*(SAIT|NAIT|MacEwan|U of A|UCalgary|.*University|.*College|.*Institute).*$',
                   '', title, flags=re.I).strip()
    if not title:
        return None

    sentences = [s.strip() for s in content.replace("\n", " ").split(".") if len(s.strip()) > 20]
    desc = ". ".join(sentences[:2]) + "." if sentences else content[:200]

    lower = (title + " " + content).lower()
    if any(x in lower for x in ["bachelor", "b.sc", "b.a.", "b.ed", "degree", "university transfer"]):
        credential = "Bachelor's Degree"
    elif any(x in lower for x in ["master", "m.sc", "m.a.", "m.eng"]):
        credential = "Master's"
    elif "diploma" in lower:
        credential = "Diploma"
    elif "apprenticeship" in lower:
        credential = "Apprenticeship"
    elif "certificate" in lower:
        credential = "Certificate"
    else:
        credential = "Program"

    duration = ""
    m = re.search(r"(\d[\d.]*)\s*[-–]?\s*(year|month|semester|week)", lower)
    if m:
        n, unit = m.group(1), m.group(2)
        duration = f"{n} {unit}{'s' if float(n) != 1 else ''}"

    domain = next((d for d in INSTITUTION_NAMES if d in url), None)
    inst   = INSTITUTION_NAMES.get(domain, "Alberta Institution")
    i_type = INSTITUTION_TYPE.get(domain, "college")

    # ── Transparency: build per-card reasoning ──────────────────────────────
    reasons = []
    if matched_term:
        reasons.append(f"Matched academic search term: \"{matched_term}\"")
    if credential != "Program":
        reasons.append(f"Credential type detected from page content: {credential}")
    if duration:
        reasons.append(f"Duration extracted from program description: {duration}")
    reasons.append(f"Source: {inst} official website ({domain or url})")
    reasons.append(f"Search query used: \"{search_query}\"")
    relevance = min(100, int((score or 0.5) * 100)) if score else None
    if relevance:
        reasons.append(f"Relevance score from search engine: {relevance}%")

    return {
        "name":             title,
        "desc":             desc[:320],
        "credential":       credential,
        "duration":         duration,
        "url":              url,
        "institution":      inst,
        "institution_type": i_type,
        "domain":           domain or "",
        # ── Transparency fields ────────────────────────────────────────────
        "matched_term":     matched_term,
        "search_query":     search_query,
        "relevance_score":  relevance,
        "reasons":          reasons,
        "source_url":       url,
        "retrieved_at":     datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }


def search_programs(career: str, domains: list[str], audit: list) -> list[dict]:
    """Search programs with full audit trail recording every decision."""
    client  = get_client()
    terms   = career_to_terms(career)
    all_raw = []

    audit.append({
        "step":    "career_interpretation",
        "input":   career,
        "output":  terms,
        "reason":  f"Mapped '{career}' to {len(terms)} academic program terms using Alberta post-secondary terminology database.",
    })

    # Strategy 1: targeted term-by-term searches
    for term in terms[:3]:
        query = f'"{term}" program course Alberta'
        try:
            t0  = time.time()
            res = client.search(query=query, include_domains=domains, max_results=5, search_depth="advanced")
            ms  = int((time.time() - t0) * 1000)
            raw = res.get("results", [])
            audit.append({
                "step":          "targeted_search",
                "query":         query,
                "domains_count": len(domains),
                "raw_results":   len(raw),
                "duration_ms":   ms,
                "reason":        f"Searched for academic term '{term}' within {len(domains)} institution domains.",
            })
            for r in raw:
                r["_matched_term"]   = term
                r["_search_query"]   = query
            all_raw.extend(raw)
        except Exception as e:
            audit.append({"step": "targeted_search_error", "query": query, "error": str(e)})

    # Strategy 2: broader fallback
    query = f"{career} diploma degree certificate program Alberta"
    try:
        t0  = time.time()
        res = client.search(query=query, include_domains=domains, max_results=5, search_depth="advanced")
        ms  = int((time.time() - t0) * 1000)
        raw = res.get("results", [])
        audit.append({
            "step":          "broad_fallback_search",
            "query":         query,
            "domains_count": len(domains),
            "raw_results":   len(raw),
            "duration_ms":   ms,
            "reason":        "Broad fallback search using original career label to catch programs not indexed under academic terms.",
        })
        for r in raw:
            r["_matched_term"]   = career
            r["_search_query"]   = query
        all_raw.extend(raw)
    except Exception as e:
        audit.append({"step": "broad_fallback_error", "query": query, "error": str(e)})

    # Parse and filter
    seen, courses = set(), []
    skipped_non_program, skipped_duplicate = 0, 0
    for r in all_raw:
        url = (r.get("url") or "").strip()
        if url in seen:
            skipped_duplicate += 1
            continue
        seen.add(url)
        parsed = _parse_result(r, r.get("_matched_term", ""), r.get("_search_query", ""))
        if parsed:
            courses.append(parsed)
        else:
            skipped_non_program += 1

    audit.append({
        "step":                 "filtering",
        "total_raw":            len(all_raw),
        "duplicates_removed":   skipped_duplicate,
        "non_program_filtered": skipped_non_program,
        "final_count":          len(courses),
        "reason":               ("Filtered out: duplicate URLs, non-program pages (news, about, events, contact), "
                                 "and pages missing program-specific keywords in title or URL."),
    })
    return courses


def get_market_insight(career: str, audit: list) -> str:
    sources = ["alis.alberta.ca", "jobbank.gc.ca", "statcan.gc.ca"]
    query   = f"{career} average salary job demand Alberta 2024 2025"
    try:
        t0  = time.time()
        res = get_client().search(query=query, include_domains=sources, max_results=2, search_depth="basic")
        ms  = int((time.time() - t0) * 1000)
        snippets = [r.get("content", "")[:280] for r in res.get("results", []) if r.get("content")]
        audit.append({
            "step":        "market_insight_search",
            "query":       query,
            "sources":     sources,
            "found":       len(snippets) > 0,
            "duration_ms": ms,
            "reason":      "Searched government labour-market sources (ALIS, Job Bank, Statistics Canada) for salary and demand data.",
        })
        return snippets[0] if snippets else ""
    except Exception as e:
        audit.append({"step": "market_insight_error", "error": str(e)})
        return ""


def build_pathway(career: str, courses: list) -> list:
    first = courses[0]["name"]        if courses else f"{career} program"
    inst  = courses[0]["institution"] if courses else "your chosen institution"
    return [
        {"step": "Confirm your prerequisites",
         "detail": "Check exact admission requirements for your chosen program. Most need Grade 12 English and Math (Pure/Applied 20-1 or equivalent)."},
        {"step": "Apply through ApplyAlberta",
         "detail": "Create a free account at applyalberta.ca — Alberta's single application portal. Apply before early-bird deadlines (usually February–March)."},
        {"step": f"Enrol in '{first}' at {inst}",
         "detail": "Attend orientation, connect with your student advisor, and ask about co-op or practicum opportunities in your first week."},
        {"step": "Complete work-integrated learning",
         "detail": "Most Alberta programs include a mandatory practicum or co-op term — many students receive their first job offer directly from their placement."},
        {"step": f"Launch your career as a {career}",
         "detail": "Graduate, write any required certification exams (Red Seal, CPNRE, APEGA, etc.), and register with the relevant Alberta professional body."},
    ]


def build_governance(career: str, terms: list, audit: list, univ_count: int, coll_count: int) -> dict:
    """Build the AI governance and transparency metadata block."""
    return {
        "system_version":    "Alberta Career Pathways v2.0",
        "model_type":        "Rule-based search + live web retrieval (no generative AI used for course matching)",
        "data_source":       "Live searches of official Alberta post-secondary institution websites via Tavily Search API",
        "search_timestamp":  datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "career_input":      career,
        "terms_used":        terms,
        "institutions_searched": len(UNIVERSITIES) + len(COLLEGES),
        "results_found":     univ_count + coll_count,
        "audit_steps":       len(audit),
        "limitations": [
            "Results depend on content indexed on institution websites at time of search.",
            "Program availability, tuition, and admission requirements change — always verify directly with the institution.",
            "Not all programs from all 26 institutions may appear; some pages may not be indexed.",
            "Career-to-term mapping covers common careers; niche roles may return broader results.",
            "Labour market data is sourced from public government databases and may not reflect current conditions.",
            "This tool is for discovery only — it is not a substitute for official academic advising.",
        ],
        "bias_disclosures": [
            "Search results are ranked by the Tavily search engine's relevance algorithm, which may favour larger institutions with more web content.",
            "Programs with more detailed web pages are more likely to appear than those with minimal online presence.",
            "Career term mapping was built from Alberta post-secondary catalogues and may reflect historical program naming conventions.",
        ],
        "human_oversight": "All recommendations should be reviewed with a qualified academic advisor before making enrollment decisions.",
        "data_privacy":    "No personal student data is stored. Career queries are used solely for the current session search.",
        "feedback_prompt": "If a result is incorrect or misleading, please report it so the career term mapping can be improved.",
        "full_audit":      audit,
    }


def discovery_query(method: str, data: dict) -> tuple[str, str]:
    if method == "shadow":
        jobs  = [data.get(f"job{i}", "") for i in range(1, 6) if data.get(f"job{i}", "")]
        return " OR ".join(jobs[:3]), jobs[0] if jobs else "your dream job"
    if method == "unjob":
        t = data.get("unjob_title", "")
        return t, t or "your chosen role"
    if method == "audit":
        subs = [data.get(f"subject{i}", "") for i in range(1, 4) if data.get(f"subject{i}", "")]
        return " ".join(subs), " & ".join(subs[:2])
    if method == "problem":
        p = data.get("problem", "")
        return p, f"solving: {p}"
    if method == "podcast":
        i = data.get("industry", "")
        return i, f"a career in {i}"
    c = data.get("career", "")
    return c, c


@app.route("/")
def index():
    return render_template("index.html")


def _stream(career: str, label: str, method: str = "direct"):
    def generate():
        audit = []
        audit.append({
            "step":   "session_start",
            "method": method,
            "input":  career,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "reason": f"Student initiated a '{method}' discovery search for: '{career}'.",
        })

        try:
            yield f"data: {json.dumps({'type':'status','msg':'Searching universities\u2026'})}\n\n"
            univ_courses = search_programs(career, UNIVERSITIES, audit)

            yield f"data: {json.dumps({'type':'status','msg':'Searching colleges \u0026 polytechnics\u2026'})}\n\n"
            coll_courses = search_programs(career, COLLEGES, audit)

            yield f"data: {json.dumps({'type':'status','msg':'Gathering market insights\u2026'})}\n\n"
            terms   = career_to_terms(career)
            insight = get_market_insight(career, audit)

            yield f"data: {json.dumps({'type':'status','msg':'Building your pathway\u2026'})}\n\n"
            all_c    = univ_courses + coll_courses
            pathway  = build_pathway(label, all_c)
            governance = build_governance(career, terms, audit, len(univ_courses), len(coll_courses))

            audit.append({
                "step":   "session_complete",
                "university_results": len(univ_courses),
                "college_results":    len(coll_courses),
                "reason": "Search complete. Results filtered, deduplicated, and structured for display.",
            })

            payload = {
                "career":       label,
                "method":       method,
                "summary":      (f"Here are specific Alberta post-secondary programs that lead to a career in "
                                 f"{label}. Results sourced live from official institution websites."),
                "insight":      insight,
                "universities": univ_courses,
                "colleges":     coll_courses,
                "pathway":      pathway,
                "governance":   governance,
            }
            yield f"data: {json.dumps({'type':'result','data':payload})}\n\n"

        except Exception as e:
            msg = str(e)
            audit.append({"step": "error", "message": msg})
            if "401" in msg or "TAVILY" in msg:
                msg = "Invalid or missing Tavily API key. Check your TAVILY_API_KEY environment variable."
            yield f"data: {json.dumps({'type':'error','msg':msg})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route("/search", methods=["POST"])
def search():
    data   = request.get_json()
    career = (data.get("career") or "").strip()
    if not career:
        return {"error": "Please enter a career goal."}, 400
    return _stream(career, career, "direct")


@app.route("/discover", methods=["POST"])
def discover():
    data   = request.get_json()
    method = (data.get("method") or "direct").strip()
    career, label = discovery_query(method, data)
    if not career.strip():
        return {"error": "Please fill in the discovery form."}, 400
    return _stream(career, label, method)


if __name__ == "__main__":
    port  = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
