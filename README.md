# Image Stack Import Template Builder

Internal web tool for Pattern's Ops Avengers team.  
Upload an **Image Links** workbook → get back a fully-built **Image Stack Import Template** sheet, with filenames resolved from the CDN.

---

## Local development

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
# → http://localhost:5000
```

---

## Deploy to Render (free tier)

### One-time setup

1. Push this repo to GitHub.
2. Go to [render.com](https://render.com) → **New → Web Service**.
3. Connect your GitHub account and select this repo.
4. Render auto-detects `render.yaml` — just click **Create Web Service**.
5. Your live URL will be something like `https://image-stack-builder.onrender.com`.

### Re-deploys

Every `git push` to `main` triggers an automatic redeploy.

---

## How it works

| Step | What happens |
|------|-------------|
| Upload | Drop your `.xlsx` workbook with the **Image Links** sheet |
| Scan | Reads Col A (Master ID), Col B (Stack Group), Col C+ (Image URLs) |
| Fetch | Resolves filenames by hitting each CDN URL (concurrent threads) |
| Write | Creates the **Image Stack Import Template** sheet in the same workbook |
| Download | Click the download button to get the result |

---

## Expected workbook structure (Image Links sheet)

| Col A | Col B | Col C | Col D | … |
|-------|-------|-------|-------|---|
| Master ID | Media Stack Group | Image URL 1 | Image URL 2 | … |
| ABC123 | Group A | https://cdn.../img1.jpg | https://cdn.../img2.jpg | |

Rows with empty Master ID **or** empty Stack Group are skipped.

---

## Advanced settings

| Setting | Default | Description |
|---------|---------|-------------|
| Threads | 10 | Concurrent HTTP requests |
| Timeout | 15s | Per-request timeout |
| Source Sheet | Image Links | Name of the input sheet |
| Output Sheet | Image Stack Import Template | Name of the output sheet |
| Referer Override | auto | Force a specific Referer header |
