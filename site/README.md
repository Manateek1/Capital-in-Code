# Capital in Code website

The public portfolio site for Capital in Code. It is a React/Vite single-page
application with client-side routes for the home page, CIC-001, methods, and
about pages.

## Development

```powershell
cd site
npm install
npm run dev
```

## Production

`npm run build` creates the deployable `dist/` directory. Vercel is configured
to serve the application and rewrite direct route visits to the client entry
point.
