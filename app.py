import os
import re
import json
from flask import Flask, render_template, request, Response, stream_with_context
from tavily import TavilyClient

app = Flask(__name__)


def get_client():
    """Lazy-init Tavily client so the app starts even before the key is set."""
    key = os.environ.get("TAVILY_API_KEY", "")
    if not key:
        raise ValueError("TAVILY_API_KEY is not set. Add it to your .env file or Render dashboard.")
    return TavilyClient(api_key=key)


def search_institution(career: str, institution: str) -> list:
    domain = "sait.ca" if institution == "sait" else "nait.ca"
    fallback_url = (
        "https://www.sait.ca/programs-and-courses"
        if institution == "sait"
        else "https://www.nait.ca/programs"
    )

    results = get_client().search(
        query=f"{career} program diploma certificate {domain}",
        include_domains=[domain],
        max_results=5,
        search_depth="advanced",
    )

    courses = []
    seen_urls = set()

    for r in results.get("results", []):
        url     = r.get("url", fallback_url)
        title   = (r.get("title") or "").strip()
        content = (r.get("content") or "").strip()

        if url in seen_urls or not title or len(content) < 40:
            continue
        seen_urls.add(url)

        sentences = [s.strip() for s in content.replace("\n", " ").split(".") if len(s.strip()) > 20]
        desc = ". ".join(sentences[:2]) + "." if sentences else content[:180]

        lower = (title + " " + content).lower()
        if "bachelor" in lower or "degree" in lower:
            credential = "Bachelor's Degree"
        elif "diploma" in lower:
            credential = "Diploma"
        elif "apprenticeship" in lower:
            credential = "Apprenticeship"
        else:
            credential = "Certificate"

        duration = ""
        m = re.search(r"(\d[\d.]*)\s*(year|month|semester|week)", lower)
        if m:
            n, unit = m.group(1), m.group(2)
            duration = f"{n} {unit}{'s' if float(n) != 1 else ''}"

        courses.append({
            "name": title,
            "desc": desc[:280],
            "credential": credential,
            "duration": duration,
            "url": url,
        })

    return courses[:4]


def get_market_insight(career: str) -> str:
    try:
        results = get_client().search(
            query=f"{career} salary demand Alberta 2024 2025",
            include_domains=["alis.alberta.ca", "jobbank.gc.ca", "statcan.gc.ca"],
            max_results=2,
            search_depth="basic",
        )
        snippets = [r.get("content", "")[:220] for r in results.get("results", []) if r.get("content")]
        return snippets[0] if snippets else ""
    except Exception:
        return ""


def build_pathway(career: str, sait: list, nait: list) -> list:
    first = (sait + nait)[0]["name"] if (sait or nait) else f"{career} program"
    return [
        {
            "step": "Research and confirm prerequisites",
            "detail": "Check admission requirements for your chosen SAIT or NAIT program. "
                      "Most require Grade 12 English and Math (Pure/Applied 20-1 or equivalent).",
        },
        {
            "step": "Apply through ApplyAlberta",
            "detail": "Create a free account at applyalberta.ca — the single portal for all Alberta "
                      "public post-secondaries. Submit before early-bird deadlines (usually February).",
        },
        {
            "step": f"Enrol in '{first}' or equivalent",
            "detail": "Choose the program that best fits your specialisation. Attend orientation and "
                      "connect with your student advisor in the first week.",
        },
        {
            "step": "Complete practicum / work-integrated learning",
            "detail": "Most Alberta polytechnic programs include a mandatory practicum or co-op term — "
                      "many students receive job offers directly from their placement employer.",
        },
        {
            "step": f"Enter the workforce as a {career}",
            "detail": "Graduate, write any required certification exams (e.g. Red Seal, CPNRE, APEGA), "
                      "and register with the relevant Alberta professional body.",
        },
    ]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    data = request.get_json()
    career = (data.get("career") or "").strip()
    if not career:
        return {"error": "Please enter a career goal."}, 400

    def generate():
        try:
            yield f"data: {json.dumps({'type': 'status', 'msg': 'Searching SAIT programs\u2026'})}\n\n"
            sait_courses = search_institution(career, "sait")

            yield f"data: {json.dumps({'type': 'status', 'msg': 'Searching NAIT programs\u2026'})}\n\n"
            nait_courses = search_institution(career, "nait")

            yield f"data: {json.dumps({'type': 'status', 'msg': 'Building your pathway\u2026'})}\n\n"
            insight = get_market_insight(career)
            pathway = build_pathway(career, sait_courses, nait_courses)

            payload = {
                "summary": (
                    f"Discover Alberta post-secondary programs that lead to a career as a {career}. "
                    "Both SAIT and NAIT offer hands-on, industry-aligned credentials recognised across the province."
                ),
                "insight": insight,
                "sait":    sait_courses,
                "nait":    nait_courses,
                "pathway": pathway,
            }
            yield f"data: {json.dumps({'type': 'result', 'data': payload})}\n\n"

        except Exception as e:
            msg = str(e)
            if "401" in msg or "invalid" in msg.lower() or "TAVILY_API_KEY" in msg:
                msg = "Invalid or missing Tavily API key. Check your TAVILY_API_KEY environment variable."
            yield f"data: {json.dumps({'type': 'error', 'msg': msg})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


if __name__ == "__main__":
    port  = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
