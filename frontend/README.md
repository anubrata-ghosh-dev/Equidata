# FairGuard Frontend (Next.js App Router)

Modern interactive frontend for FairGuard - AI Bias Auditor.

## Tech Stack

- Next.js (App Router)
- Tailwind CSS
- Axios
- Recharts
- TypeScript

## Folder Structure

frontend/
├── app/
│   ├── page.tsx
│   ├── simulate/
│   │   └── page.tsx
│   ├── audit/
│   │   └── page.tsx
├── components/
│   ├── ScenarioCard.tsx
│   ├── InputForm.tsx
│   ├── ResultCard.tsx
│   ├── BiasAlert.tsx
│   ├── Charts.tsx
│   ├── Navbar.tsx
├── services/
│   └── api.ts
├── styles/
├── public/
├── package.json
└── README.md

## Run Locally

1. Start backend first on port 8000.
2. In this folder:

npm install
npm run dev

Open http://localhost:3000

## Product Flow

- Home page: choose Hiring, Loan Approval, or College Admission
- Simulator page:
  - fill form fields
  - click Get Decision (calls POST /predict)
  - if bias is flagged, warning appears
  - click Fix Bias (calls POST /mitigate)
- Audit page:
  - bar chart for male vs female selection rates
  - before vs after fairness chart

## API Base URL

Configured in services/api.ts:

http://127.0.0.1:8000

## Notes

- Browser requests require backend CORS enabled for localhost:3000.
- Audit page shows fallback demo data if no mitigation run has been completed yet.
