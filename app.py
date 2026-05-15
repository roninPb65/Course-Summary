import os
import re
import json
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

# ── Known program-listing pages (used for targeted extraction) ──────────────
PROGRAM_PAGES = {
    "sait.ca":               "https://www.sait.ca/programs-and-courses",
    "nait.ca":               "https://www.nait.ca/programs",
    "macewan.ca":            "https://www.macewan.ca/programs-and-courses/",
    "mtroyal.ca":            "https://www.mtroyal.ca/ProgramsCourses/",
    "ualberta.ca":           "https://www.ualberta.ca/programs/index.html",
    "ucalgary.ca":           "https://www.ucalgary.ca/future-students/undergraduate/explore-programs",
    "ulethbridge.ca":        "https://www.ulethbridge.ca/programs",
    "bowvalleycollege.ca":   "https://bowvalleycollege.ca/programs-courses",
    "reddeer.ca":            "https://www.reddeer.ca/programs-and-courses/",
    "lethbridgecollege.ca":  "https://lethbridgecollege.ca/departments/programs-and-courses",
    "norquest.ca":           "https://www.norquest.ca/programs-courses/",
    "concordia.ab.ca":       "https://concordia.ab.ca/programs/",
    "athabascau.ca":         "https://www.athabascau.ca/programs/",
    "auarts.ca":             "https://www.auarts.ca/academics/programs",
    "nwpolytech.ca":         "https://nwpolytech.ca/programs-courses/",
}

# ── Career → specific academic program terms ───────────────────────────────
# Maps common career goals to the real program names used by Alberta institutions
CAREER_TERM_MAP = {
    # Technology
    "software developer":      ["software development", "computer systems technology", "computing science", "software engineering technology"],
    "software engineer":       ["software engineering", "computing science", "computer engineering", "software development"],
    "web developer":           ["web development", "internet communications technology", "digital media", "web design and development"],
    "data scientist":          ["data analytics", "data science", "statistics", "machine learning", "business intelligence"],
    "cybersecurity":           ["cybersecurity", "information security", "network security", "information systems security"],
    "network administrator":   ["computer networking", "network administration", "IT systems", "information technology"],
    "game developer":          ["game development", "interactive digital media", "3D animation", "digital arts"],
    "ai developer":            ["artificial intelligence", "machine learning", "data science", "computing science"],
    "database administrator":  ["database administration", "information technology", "computer systems", "data management"],

    # Health & Medical
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

    # Engineering
    "engineer":                ["engineering", "engineering technology", "applied science"],
    "civil engineer":          ["civil engineering", "civil engineering technology", "structural engineering"],
    "mechanical engineer":     ["mechanical engineering", "mechanical engineering technology", "mechatronics"],
    "electrical engineer":     ["electrical engineering", "electrical engineering technology", "power engineering"],
    "petroleum engineer":      ["petroleum engineering", "oil and gas", "chemical engineering", "energy"],
    "environmental engineer":  ["environmental engineering", "environmental technology", "environmental science"],
    "chemical engineer":       ["chemical engineering", "chemical technology", "process engineering"],
    "aerospace engineer":      ["aerospace engineering", "avionics", "aviation", "aeronautical"],

    # Trades
    "electrician":             ["electrical apprenticeship", "electrical technology", "industrial electrician", "power engineering"],
    "plumber":                 ["plumbing apprenticeship", "plumber journeyman", "pipefitting"],
    "welder":                  ["welding", "welding fabrication", "metal fabrication", "welding technology"],
    "carpenter":               ["carpentry", "construction", "building construction technology"],
    "hvac":                    ["HVAC", "refrigeration and air conditioning", "building systems", "plumbing and heating"],
    "mechanic":                ["automotive service technology", "auto mechanic", "heavy equipment technology"],
    "heavy equipment":         ["heavy equipment technology", "heavy equipment operator", "construction equipment"],

    # Business & Finance
    "accountant":              ["accounting", "CPA", "bachelor of commerce", "financial management"],
    "business analyst":        ["business analysis", "management information systems", "business administration", "commerce"],
    "marketing":               ["marketing", "digital marketing", "advertising", "business marketing"],
    "human resources":         ["human resources management", "HR management", "people management", "HRM"],
    "project manager":         ["project management", "business administration", "management"],
    "entrepreneur":            ["entrepreneurship", "business administration", "new venture", "small business"],

    # Creative & Design
    "graphic designer":        ["graphic design", "graphic communications", "visual communications", "digital design"],
    "ux designer":             ["UX design", "user experience design", "interaction design", "digital design"],
    "animator":                ["animation", "3D animation", "motion graphics", "digital media arts"],
    "photographer":            ["photography", "photographic arts", "visual arts", "media arts"],
    "filmmaker":               ["film production", "digital video", "film studies", "media production"],
    "interior designer":       ["interior design", "interior decorating", "architectural technology"],
    "architect":               ["architecture", "architectural technology", "architectural design"],
    "fashion designer":        ["fashion design", "fashion arts", "textile design"],

    # Education & Social
    "teacher":                 ["education", "bachelor of education", "BEd", "teaching certificate"],
    "early childhood":         ["early childhood education", "ECE", "child and youth care", "early learning"],
    "social worker":           ["social work", "BSW bachelor of social work", "social sciences"],
    "psychologist":            ["psychology", "counselling", "mental health", "applied psychology"],
    "counsellor":              ["counselling", "social work", "psychology", "addictions counselling"],

    # Environment & Agriculture
    "environmental scientist": ["environmental science", "ecology", "environmental studies", "natural resources"],
    "biologist":               ["biology", "biological sciences", "life sciences", "ecology"],
    "agriculturalist":         ["agriculture", "agribusiness", "agronomy", "animal science", "crop science"],
    "veterinarian":            ["veterinary technology", "animal health technology", "pre-vet biology"],
    "geologist":               ["geology", "earth sciences", "geophysics", "petroleum geology"],
    "forest":                  ["forestry", "forest technology", "environmental resource science"],

    # Hospitality & Tourism
    "chef":                    ["culinary arts", "baking and pastry arts", "cook apprenticeship", "food service management"],
    "hotel manager":           ["hospitality management", "hotel management", "tourism management"],
    "event planner":           ["event management", "hospitality", "tourism management"],

    # Legal & Law Enforcement
    "police officer":          ["police studies", "law enforcement", "justice studies", "criminal justice"],
    "lawyer":                  ["pre-law", "law", "legal studies", "political science", "criminology"],
    "paralegal":               ["paralegal studies", "legal assistant", "law clerk"],

    # Transport & Aviation
    "pilot":                   ["aviation", "flight training", "commercial pilot", "aeronautical"],
    "logistics":               ["supply chain management", "logistics", "transportation management"],
}


def get_client() -> TavilyClient:
    key = os.environ.get("TAVILY_API_KEY", "")
    if not key:
        raise ValueError("TAVILY_API_KEY is not set. Add it to your .env file or Render dashboard.")
    return TavilyClient(api_key=key)


def career_to_terms(career: str) -> list[str]:
    """
    Map a career string to specific academic program terms used by Alberta institutions.
    Falls back gracefully for unrecognised careers.
    """
    career_lower = career.lower().strip()

    # Exact match
    if career_lower in CAREER_TERM_MAP:
        return CAREER_TERM_MAP[career_lower]

    # Partial match — find the closest key
    for key, terms in CAREER_TERM_MAP.items():
        if key in career_lower or career_lower in key:
            return terms

    # Word-level match
    words = career_lower.split()
    for key, terms in CAREER_TERM_MAP.items():
        if any(w in key for w in words):
            return terms

    # No match — build generic academic terms from the career string
    base = career.strip()
    return [
        base,
        f"{base} program",
        f"{base} technology",
        f"{base} diploma",
        f"bachelor of {base}",
        f"applied {base}",
    ]


def _is_program_page(url: str, title: str) -> bool:
    """Return True if the URL/title looks like an actual program page, not a home/about page."""
    url_lower   = url.lower()
    title_lower = title.lower()

    # Skip obvious non-program pages
    skip_patterns = [
        "/news", "/events", "/about", "/contact", "/faculty",
        "/research", "/campus", "/student-services", "/jobs",
        "/library", "/athletics", "login", "apply-now",
    ]
    if any(p in url_lower for p in skip_patterns):
        return False

    # Prefer pages with program-like path segments
    good_url_segments = [
        "program", "course", "diploma", "certificate", "degree",
        "bachelor", "major", "credential", "study",
    ]
    good_title_words = [
        "diploma", "certificate", "degree", "bachelor", "program",
        "technology", "technician", "science", "engineering", "management",
        "arts", "design", "nursing", "education", "apprenticeship",
    ]
    url_ok   = any(s in url_lower   for s in good_url_segments)
    title_ok = any(w in title_lower for w in good_title_words)
    return url_ok or title_ok


def _parse_result(r: dict) -> dict | None:
    """Parse a single Tavily result into a clean course dict."""
    url     = (r.get("url") or "").strip()
    title   = (r.get("title") or "").strip()
    content = (r.get("content") or "").strip()

    if not title or len(content) < 30:
        return None
    if not _is_program_page(url, title):
        return None

    # Clean up title — remove institution name suffix (e.g. "| SAIT")
    title = re.sub(r'\s*[|\-–—]\s*(SAIT|NAIT|MacEwan|U of A|UCalgary|.*University|.*College).*$', '', title, flags=re.I).strip()
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
    return {
        "name":             title,
        "desc":             desc[:320],
        "credential":       credential,
        "duration":         duration,
        "url":              url,
        "institution":      INSTITUTION_NAMES.get(domain, "Alberta Institution"),
        "institution_type": INSTITUTION_TYPE.get(domain, "college"),
        "domain":           domain or "",
    }


def search_programs(career: str, domains: list[str]) -> list[dict]:
    """
    Run multiple targeted Tavily searches for a career across a set of institution domains.
    Uses academic program terms so results are actual course names, not generic pages.
    """
    client = get_client()
    terms  = career_to_terms(career)
    all_results = []

    # Strategy 1: search top 3 academic terms against the institution group
    for term in terms[:3]:
        try:
            res = client.search(
                query=f'"{term}" program course Alberta',
                include_domains=domains,
                max_results=5,
                search_depth="advanced",
            )
            all_results.extend(res.get("results", []))
        except Exception:
            pass

    # Strategy 2: broader search with original career title (catches edge cases)
    try:
        res = client.search(
            query=f'{career} diploma degree certificate program Alberta',
            include_domains=domains,
            max_results=5,
            search_depth="advanced",
        )
        all_results.extend(res.get("results", []))
    except Exception:
        pass

    # Parse, filter, deduplicate
    seen, courses = set(), []
    for r in all_results:
        url = (r.get("url") or "").strip()
        if url in seen:
            continue
        seen.add(url)
        parsed = _parse_result(r)
        if parsed:
            courses.append(parsed)

    return courses


def get_market_insight(career: str) -> str:
    try:
        res = get_client().search(
            query=f"{career} average salary job demand Alberta 2024 2025",
            include_domains=["alis.alberta.ca", "jobbank.gc.ca", "statcan.gc.ca", "indeed.com"],
            max_results=2,
            search_depth="basic",
        )
        snippets = [r.get("content", "")[:280] for r in res.get("results", []) if r.get("content")]
        return snippets[0] if snippets else ""
    except Exception:
        return ""


def build_pathway(career: str, courses: list) -> list:
    first = courses[0]["name"]        if courses else f"{career} program"
    inst  = courses[0]["institution"] if courses else "your chosen institution"
    return [
        {"step": "Confirm your prerequisites",
         "detail": "Check exact admission requirements for your chosen program. Most need "
                   "Grade 12 English and Math (Pure/Applied 20-1 or equivalent)."},
        {"step": "Apply through ApplyAlberta",
         "detail": "Create a free account at applyalberta.ca — Alberta's single application portal. "
                   "Apply before early-bird deadlines (usually February–March)."},
        {"step": f"Enrol in '{first}' at {inst}",
         "detail": "Attend orientation, connect with your student advisor, and ask about "
                   "co-op or practicum opportunities in your first week."},
        {"step": "Complete work-integrated learning",
         "detail": "Most Alberta programs include a mandatory practicum or co-op term — "
                   "many students receive their first job offer directly from their placement."},
        {"step": f"Launch your career as a {career}",
         "detail": "Graduate, write any required certification exams (Red Seal, CPNRE, APEGA, etc.), "
                   "and register with the relevant Alberta professional body."},
    ]


# ── Discovery helpers ───────────────────────────────────────────────────────

def discovery_query(method: str, data: dict) -> tuple[str, str]:
    """Return (career_query, display_label) for each discovery method."""
    if method == "shadow":
        jobs  = [data.get(f"job{i}", "") for i in range(1, 6)]
        jobs  = [j for j in jobs if j]
        label = jobs[0] if jobs else "your dream job"
        # Combine first 3 jobs into a search
        return " OR ".join(jobs[:3]), label

    if method == "unjob":
        title = data.get("unjob_title", "")
        return title, title or "your chosen role"

    if method == "audit":
        subjects = [data.get(f"subject{i}", "") for i in range(1, 4)]
        subjects = [s for s in subjects if s]
        label    = " & ".join(subjects[:2])
        return " ".join(subjects), label

    if method == "problem":
        problem = data.get("problem", "")
        return problem, f"solving: {problem}"

    if method == "podcast":
        industry = data.get("industry", "")
        return industry, f"a career in {industry}"

    career = data.get("career", "")
    return career, career


@app.route("/")
def index():
    return render_template("index.html")


def _stream(career: str, label: str, method: str = "direct"):
    def generate():
        try:
            yield f"data: {json.dumps({'type':'status','msg':'Searching universities\u2026'})}\n\n"
            university_courses = search_programs(career, UNIVERSITIES)

            yield f"data: {json.dumps({'type':'status','msg':'Searching colleges \u0026 polytechnics\u2026'})}\n\n"
            college_courses = search_programs(career, COLLEGES)

            yield f"data: {json.dumps({'type':'status','msg':'Gathering market insights\u2026'})}\n\n"
            insight  = get_market_insight(career)
            all_c    = university_courses + college_courses
            pathway  = build_pathway(label, all_c)

            yield f"data: {json.dumps({'type':'status','msg':'Building your pathway\u2026'})}\n\n"

            payload = {
                "career":       label,
                "method":       method,
                "summary":      (f"Here are specific Alberta post-secondary programs that lead to a career in "
                                 f"{label}. Results are sourced live from institution websites across the province."),
                "insight":      insight,
                "universities": university_courses,
                "colleges":     college_courses,
                "pathway":      pathway,
            }
            yield f"data: {json.dumps({'type':'result','data':payload})}\n\n"

        except Exception as e:
            msg = str(e)
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
