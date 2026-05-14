import os
import json
import anthropic
from flask import Flask, render_template, request, jsonify, Response, stream_with_context

app = Flask(__name__)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def build_prompt(career: str) -> str:
    return f"""You are an expert Alberta post-secondary education advisor. A student wants to become a "{career}".

Search the SAIT (sait.ca) and NAIT (nait.ca) websites to find the most relevant programs and courses for this career goal.

Respond in EXACTLY this JSON format (valid JSON only, no markdown fences):

{{
  "summary": "2 sentence overview of this career path in Alberta",
  "insight": "1-2 sentences about Alberta job market and salary outlook for this role",
  "sait": [
    {{
      "name": "Program name",
      "desc": "2 sentence description",
      "duration": "e.g. 2 years",
      "credential": "e.g. Diploma",
      "area": "e.g. Technology",
      "url": "actual URL from sait.ca or https://www.sait.ca/programs-and-courses"
    }}
  ],
  "nait": [
    {{
      "name": "Program name",
      "desc": "2 sentence description",
      "duration": "e.g. 2 years",
      "credential": "e.g. Diploma",
      "area": "e.g. Technology",
      "url": "actual URL from nait.ca or https://www.nait.ca/programs"
    }}
  ],
  "pathway": [
    {{
      "step": "Step title",
      "detail": "Specific detail about what to do"
    }}
  ]
}}

Include 3-4 SAIT programs, 3-4 NAIT programs, and 4-5 pathway steps."""


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    data = request.get_json()
    career = (data.get("career") or "").strip()
    if not career:
        return jsonify({"error": "Please enter a career goal."}), 400

    def generate():
        try:
            yield f"data: {json.dumps({'type': 'status', 'msg': 'Searching SAIT programs\u2026'})}\n\n"

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{"role": "user", "content": build_prompt(career)}],
            )

            yield f"data: {json.dumps({'type': 'status', 'msg': 'Searching NAIT programs\u2026'})}\n\n"

            full_text = ""
            for block in response.content:
                if block.type == "text":
                    full_text += block.text

            yield f"data: {json.dumps({'type': 'status', 'msg': 'Building your pathway\u2026'})}\n\n"

            # Strip markdown fences if present
            cleaned = full_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            cleaned = cleaned.strip()

            result = json.loads(cleaned)
            yield f"data: {json.dumps({'type': 'result', 'data': result})}\n\n"

        except json.JSONDecodeError:
            yield f"data: {json.dumps({'type': 'error', 'msg': 'Could not parse AI response. Please try again.'})}\n\n"
        except anthropic.AuthenticationError:
            yield f"data: {json.dumps({'type': 'error', 'msg': 'Invalid API key. Check your ANTHROPIC_API_KEY environment variable.'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'msg': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
