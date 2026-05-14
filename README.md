# 🎓 Alberta Career Pathways

> An AI-powered education pathway tool — APAS × SAIT × NAIT

[![CI](https://github.com/YOUR_USERNAME/alberta-career-pathways/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/alberta-career-pathways/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/flask-3.0-black?logo=flask)](https://flask.palletsprojects.com)
[![Anthropic](https://img.shields.io/badge/powered%20by-Tavily-blue)](https://anthropic.com)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A proof-of-concept aligned with the **APAS Partnership with SAIT for AI Student Capstone Placements** initiative. Students enter a career goal and receive personalised program recommendations from SAIT and NAIT, sourced via live AI-powered web search, along with a step-by-step pathway and Alberta labour market insights.

---

## ✨ Features

- 🔍 **Live web search** — scrapes sait.ca and nait.ca in real time via Claude's web search tool
- 🎯 **Personalised pathways** — step-by-step roadmap from high school to career entry
- 📊 **Labour market insights** — Alberta-specific salary and demand outlook per role
- ⚡ **Streaming UX** — results stream back via Server-Sent Events (no page reload)
- 📱 **Responsive** — works on desktop, tablet, and mobile
- 🔗 **Direct links** — every program card links to the actual institution page

---

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/alberta-career-pathways.git
cd alberta-career-pathways
```

### 2. Create a virtual environment

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your Tavily API key:

```
TAVILY_API_KEY=tvly-your-key-here
FLASK_ENV=development
```

> Get your API key at [app.tavily.com](https://app.tavily.com)

### 5. Run the app

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

---

## 🗂 Project Structure

```
alberta-career-pathways/
├── app.py                        ← Flask backend + Anthropic API integration
├── requirements.txt              ← Python dependencies
├── Procfile                      ← Gunicorn start command (Railway / Heroku)
├── render.yaml                   ← One-click Render.com deploy config
├── .env.example                  ← Environment variable template
├── .gitignore
├── LICENSE
├── README.md
├── templates/
│   └── index.html                ← Jinja2 HTML template
├── static/
│   ├── style.css                 ← All styles (CSS variables, responsive)
│   └── main.js                   ← Frontend logic (SSE, card builders, routing)
└── .github/
    └── workflows/
        └── ci.yml                ← GitHub Actions: lint + import check
```

---

## 🏗 How It Works

```
User types career goal
        │
        ▼
POST /search  ──►  Flask receives request
                        │
                        ▼
               Anthropic Claude API
               (claude-sonnet-4, web_search tool)
                        │
               Searches sait.ca + nait.ca live
                        │
                        ▼
               Structured JSON response
               (programs, pathway, insights)
                        │
                        ▼
          Server-Sent Events stream to browser
                        │
                        ▼
             UI renders cards + pathway
```

---

## ☁️ Deployment

### Render.com (recommended — free tier available)

1. Fork this repo
2. Connect to [render.com](https://render.com) → **New Web Service** → select your fork
3. Render auto-detects `render.yaml`
4. Add `TAVILY_API_KEY` in the **Environment** tab
5. Deploy ✅

### Railway

1. Connect repo at [railway.app](https://railway.app)
2. Add `TAVILY_API_KEY` environment variable
3. Railway uses the `Procfile` automatically

### Heroku

```bash
heroku create alberta-career-pathways
heroku config:set TAVILY_API_KEY=sk-ant-...
git push heroku main
```

### Docker (self-hosted)

```bash
docker build -t alberta-pathways .
docker run -p 5000:5000 -e TAVILY_API_KEY=sk-ant-... alberta-pathways
```

---

## 🔧 Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TAVILY_API_KEY` | ✅ Yes | — | Your Tavily API key |
| `FLASK_ENV` | No | `production` | `development` enables debug mode |
| `PORT` | No | `5000` | Port to listen on |

---

## 🤝 Alignment with APAS Vision

This project directly supports the goals outlined in the **APAS Partnership with SAIT for AI Student Capstone Placements** briefing:

| APAS Goal | Implementation |
|-----------|---------------|
| AI-powered personalised pathways | Claude API with live web search per learner query |
| Replace static tools (ALIS, Career Cruising) | Dynamic results from sait.ca / nait.ca in real time |
| Reduce manual content maintenance | AI generates and updates content automatically |
| Link learners to Alberta post-secondary programs | Every card links directly to the institution page |
| Support ApplyAlberta integration | CTA button links to applyalberta.ca |
| Data-driven learner insights | Labour market data surfaced per career goal |

---

## 📄 License

MIT © 2025 — see [LICENSE](LICENSE)
