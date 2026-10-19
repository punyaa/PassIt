# PassIt Web

Next.js App Router frontend shared by two owners:

- **F1 Front core:** design system, app shell, auth, search, listing creation/details and booking views.
- **F2 Front transaction:** handover, return, damage, dashboards and reviews.

F1 owns shared components under `components/`. F2 imports those components rather than duplicating them. Both owners use the generated OpenAPI types and MSW handlers, so frontend work does not wait for backend implementation.

```bash
npm ci
npm run generate:api
npm run dev
```

The UI keeps the established forest, cream and orange PassIt visual language. Shared components belong in `components/`; route-specific code belongs beside its App Router page.
