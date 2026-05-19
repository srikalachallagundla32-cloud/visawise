# Visawise

**H1B sponsor intelligence platform** — find companies that actually sponsor visas.

Visawise processes 268,801 public USCIS petitions across 29,440 companies and surfaces sponsorship risk intelligence that doesn't exist anywhere else in a clean, usable interface.

🔗 **[Live demo](https://visawise.vercel.app)** · **[API docs](https://visawise-api.railway.app/docs)**

---

![Visawise screenshot](docs/screenshot.png)

---

## What it does

Most H1B job seekers waste weeks applying to companies that have never sponsored a visa, or worse — companies that quietly drop visa holders after layoffs. Visawise fixes that.

- **Sponsor score** — every company gets a 0–100 score based on 5 years of approval rate, petition volume, and filing consistency
- **Risk classification** — very safe / safe / moderate / risky based on historical patterns
- **Filing history** — year-by-year breakdown of approvals vs denials from 2019–2023
- **Real-time search** — instant search across 29,440 companies with debounced API calls
- **Odds calculator** — personalized sponsorship probability based on your role and target company

---

## Tech stack

### Frontend
| Technology | Purpose |
|---|---|
| Next.js 14 (App Router) | React framework, file-based routing |
| TypeScript | Full type safety across components |
| Tailwind CSS | Utility-first styling |
| Recharts | Filing history bar charts |
| Framer Motion | Score ring animations |

### Backend
| Technology | Purpose |
|---|---|
| FastAPI | REST API with auto-generated OpenAPI docs |
| Pandas | In-memory DataFrame for sub-10ms queries |
| Uvicorn | ASGI server |
| Pydantic | Response model validation |
| Python 3.13 | Runtime |

### Data pipeline
| Technology | Purpose |
|---|---|
| USCIS H1B disclosure data | 5 years of public petition records |
| Pandas ETL | Schema normalization across fiscal years |
| Custom scoring algorithm | Approval rate + volume + consistency |
| CSV → processed data | 268,801 rows → 29,440 scored companies |

### Tooling
```
Ruff          Python linter and formatter
Git + GitHub  Version control
Vercel        Frontend deployment
Railway       Backend deployment
```

---

## Architecture

```
visawise/
├── pipeline/
│   ├── download.py       # Auto-discovers USCIS CSV files
│   └── clean.py          # ETL: normalize, clean, score
├── api/
│   └── main.py           # FastAPI: search, profiles, stats
├── data/
│   ├── raw/              # USCIS source CSVs (not committed)
│   └── processed/        # company_scores.csv, h1b_combined.csv
└── visawise-frontend/
    └── app/
        └── page.tsx      # Next.js App Router main page
```

---

## API endpoints

```
GET /                          Platform info and stats
GET /companies/top             Top H1B sponsors (filterable by state)
GET /companies/search?q=       Real-time company search
GET /companies/{name}          Full company profile + yearly history
GET /stats                     Global dataset statistics
```

Interactive docs available at `/docs` when running locally.

---

## Getting started

### 1. Clone the repo

```bash
git clone https://github.com/srikalachallagundla32-cloud/visawise.git
cd visawise
```

### 2. Set up the backend

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Download USCIS H1B disclosure CSVs from [uscis.gov](https://www.uscis.gov/tools/reports-and-studies/h-1b-employer-data-hub) and place them in `data/raw/` named `h1b_2019.csv` through `h1b_2023.csv`.

```bash
python3 pipeline/clean.py
uvicorn api.main:app --reload
```

API is now running at `http://127.0.0.1:8000`

### 3. Set up the frontend

```bash
cd visawise-frontend
npm install
npm run dev
```

Frontend is now running at `http://localhost:3000`

---

## Scoring algorithm

Each company receives a sponsor score from 0–100 computed from three factors:

| Factor | Weight | Description |
|---|---|---|
| Approval rate | 60% | Total approvals / total petitions |
| Volume | 25% | Log-scale petition count (capped at 1,000) |
| Consistency | 15% | Number of years with active filings out of 5 |

Companies with fewer than 5 total petitions are excluded.

---

## Data source

All data comes from the [USCIS H1B Employer Data Hub](https://www.uscis.gov/tools/reports-and-studies/h-1b-employer-data-hub) — a public government dataset updated annually. No scraping, no private data.

Fiscal years covered: **2019, 2020, 2021, 2022, 2023**

---

## Why I built this

I built Visawise while on an H1B visa with 60 days to find a new job. The problem was real and immediate — I needed to know which companies were actually safe to apply to, not just which ones listed "visa sponsorship available" on job boards.

The USCIS data existed. Nobody had built a clean, fast interface on top of it. So I did.

---

## Roadmap

- [ ] Deploy frontend to Vercel
- [ ] Deploy API to Railway
- [ ] Odds calculator (client-side logistic regression)
- [ ] Filter by state and industry
- [ ] Email alerts for watchlisted companies
- [ ] 2024 data when released by USCIS

---

## License

MIT