import os
import re
import json
from flask import Flask, render_template, request, Response, stream_with_context
from tavily import TavilyClient

app = Flask(__name__)

# ── All 26 Alberta publicly-funded post-secondary institutions ──────────────
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


def get_client():
    key = os.environ.get("TAVILY_API_KEY", "")
    if not key:
        raise ValueError("TAVILY_API_KEY is not set. Add it to your .env file or Render dashboard.")
    return TavilyClient(api_key=key)


def _parse_results(raw: list) -> list:
    courses, seen = [], set()
    for r in raw:
        url     = (r.get("url") or "").strip()
        title   = (r.get("title") or "").strip()
        content = (r.get("content") or "").strip()
        if url in seen or not title or len(content) < 40:
            continue
        seen.add(url)

        sentences = [s.strip() for s in content.replace("\n", " ").split(".") if len(s.strip()) > 20]
        desc = ". ".join(sentences[:2]) + "." if sentences else content[:200]

        lower = (title + " " + content).lower()
        if any(x in lower for x in ["bachelor", "b.sc", "b.a.", "b.ed", "degree"]):
            credential = "Bachelor's Degree"
        elif any(x in lower for x in ["master", "m.sc", "m.a."]):
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
        m = re.search(r"(\d[\d.]*)\s*(year|month|semester|week)", lower)
        if m:
            n, unit = m.group(1), m.group(2)
            duration = f"{n} {unit}{'s' if float(n) != 1 else ''}"

        domain = next((d for d in INSTITUTION_NAMES if d in url), None)
        courses.append({
            "name":             title,
            "desc":             desc[:300],
            "credential":       credential,
            "duration":         duration,
            "url":              url,
            "institution":      INSTITUTION_NAMES.get(domain, "Alberta Institution"),
            "institution_type": INSTITUTION_TYPE.get(domain, "college"),
            "domain":           domain or "",
        })
    return courses


def search_all_institutions(query: str) -> list:
    client = get_client()
    all_courses = []
    for domains in [UNIVERSITIES, COLLEGES]:
        try:
            res = client.search(
                query=query,
                include_domains=domains,
                max_results=6,
                search_depth="advanced",
            )
            all_courses += _parse_results(res.get("results", []))
        except Exception:
            pass
    # deduplicate
    seen, unique = set(), []
    for c in all_courses:
        if c["url"] not in seen:
            seen.add(c["url"])
            unique.append(c)
    return unique


def get_market_insight(career: str) -> str:
    try:
        res = get_client().search(
            query=f"{career} salary demand Alberta 2024 2025",
            include_domains=["alis.alberta.ca", "jobbank.gc.ca", "statcan.gc.ca"],
            max_results=2,
            search_depth="basic",
        )
        return next((r["content"][:260] for r in res.get("results", []) if r.get("content")), "")
    except Exception:
        return ""


def build_pathway(career: str, courses: list) -> list:
    first = courses[0]["name"] if courses else f"{career} program"
    inst  = courses[0]["institution"] if courses else "your chosen institution"
    return [
        {"step": "Confirm your prerequisites",
         "detail": "Check admission requirements for your chosen program. Most need Grade 12 English "
                   "and Math (Pure/Applied 20-1 or equivalent)."},
        {"step": "Apply through ApplyAlberta",
         "detail": "Create a free account at applyalberta.ca — Alberta's single application portal. "
                   "Submit before early-bird deadlines (usually February)."},
        {"step": f"Enrol in '{first}' at {inst}",
         "detail": "Attend orientation week, connect with your student advisor, and explore "
                   "co-op or practicum opportunities early."},
        {"step": "Complete work-integrated learning",
         "detail": "Most Alberta programs include a practicum or co-op term — "
                   "many students receive their first job offer directly from placement."},
        {"step": f"Launch your career as a {career}",
         "detail": "Graduate, write any certification exams (Red Seal, CPNRE, APEGA, etc.), "
                   "and register with the relevant Alberta professional body."},
    ]


# ── Discovery method → search query mappings ───────────────────────────────
def discovery_query(method: str, data: dict) -> tuple[str, str]:
    """Return (search_query, career_label) for each discovery method."""
    if method == "shadow":
        jobs  = " OR ".join(filter(None, [data.get(f"job{i}") for i in range(1, 6)]))
        label = data.get("job1", "your dream job")
        return f"{jobs} program diploma degree Alberta", label

    if method == "unjob":
        title = data.get("unjob_title", "")
        label = title or "your chosen role"
        return f"{title} related degree diploma Alberta program", label

    if method == "audit":
        subjects = " ".join(filter(None, [data.get(f"subject{i}") for i in range(1, 4)]))
        label = data.get("subject1", "your interests")
        return f"{subjects} Alberta program degree diploma", label

    if method == "problem":
        problem = data.get("problem", "")
        label   = f"solving '{problem}'"
        return f"{problem} field of study Alberta program degree", label

    if method == "podcast":
        industry = data.get("industry", "")
        label    = f"a career in {industry}"
        return f"{industry} program career Alberta degree diploma", label

    # default / direct
    career = data.get("career", "")
    return f"{career} program diploma degree Alberta", career


@app.route("/")
def index():
    return render_template("index.html")


def _stream_search(query: str, career_label: str, method: str = "direct"):
    def generate():
        try:
            yield f"data: {json.dumps({'type': 'status', 'msg': 'Searching universities\u2026'})}\n\n"
            all_courses  = search_all_institutions(query)

            yield f"data: {json.dumps({'type': 'status', 'msg': 'Gathering market insights\u2026'})}\n\n"
            insight  = get_market_insight(career_label)
            pathway  = build_pathway(career_label, all_courses)

            universities = [c for c in all_courses if c["institution_type"] == "university"]
            colleges     = [c for c in all_courses if c["institution_type"] == "college"]

            yield f"data: {json.dumps({'type': 'status', 'msg': 'Building your pathway\u2026'})}\n\n"
            payload = {
                "career":       career_label,
                "method":       method,
                "summary":      (f"Explore Alberta post-secondary programs aligned with {career_label}. "
                                 "Results span all 26 publicly-funded institutions province-wide."),
                "insight":      insight,
                "universities": universities,
                "colleges":     colleges,
                "pathway":      pathway,
            }
            yield f"data: {json.dumps({'type': 'result', 'data': payload})}\n\n"

        except Exception as e:
            msg = str(e)
            if "401" in msg or "TAVILY" in msg:
                msg = "Invalid or missing Tavily API key. Check your TAVILY_API_KEY environment variable."
            yield f"data: {json.dumps({'type': 'error', 'msg': msg})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route("/search", methods=["POST"])
def search():
    data   = request.get_json()
    career = (data.get("career") or "").strip()
    if not career:
        return {"error": "Please enter a career goal."}, 400
    query  = f"{career} program diploma degree certificate Alberta"
    return _stream_search(query, career, "direct")


@app.route("/discover", methods=["POST"])
def discover():
    data   = request.get_json()
    method = (data.get("method") or "direct").strip()
    query, label = discovery_query(method, data)
    if not query.strip():
        return {"error": "Please fill in the discovery form."}, 400
    return _stream_search(query, label, method)


if __name__ == "__main__":
    port  = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
