# Capstone Productivity Dashboard

Local React + TypeScript dashboard for your engineering capstone business pitch.

## Run locally

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
npm run preview
```

## Notes

- Uses the bundled `src/data/productivity_data.json` by default
- You can upload a replacement JSON file from the UI
- Repository charts are based on matched productivity events
- Matching uses nearest workflow completion timestamp with confidence thresholds
