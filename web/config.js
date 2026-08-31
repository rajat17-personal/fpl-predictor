// Deployment config for the static site.
//
// API_BASE:
//   null  -> auto-detect (recommended for local dev): the page probes its own
//            origin first (covers `uvicorn api.main:app --port 8000`, which
//            serves site + API together), then http://localhost:8001 (covers
//            the two-process setup with python -m http.server).
//   "https://api.example.com" -> production: set your deployed API origin.
window.FPL_CONFIG = { API_BASE: null };
