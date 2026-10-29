# Demo content

The seed bundles 20 fictional lender profiles, 40 listings and 15 rental scenarios. Each listing has a cover photo; eight have additional views. `catalogue.json` records the source page and original URL for each bundled image, alongside original demo descriptions. Images come from marketplace, resale and rental sources; seller identities and reviews are not imported. JPEGs have metadata removed and their longest edge is at most 1280px.

Seeding requires no image searches or external image downloads. The existing presigned upload flow stores the bundled files in local media storage or S3. Listing photos and condition evidence receive separate upload keys. No new runtime dependency is required.

Scenario dates are offsets from the day the seed runs. The seed creates real bookings, checklists, settlements and reviews through the application API, then applies historical fixture dates to the booking, evidence, reviews and ledger timestamps. This keeps past rentals in the past without relaxing production validation. Fees whose hold has ended are released through the existing idempotent release service.

Run `python -m scripts.seed --reset` from the API directory or container. The reset replaces all database data, including saved listings; existing media objects are retained by the storage backend. Existing demo emails and passwords remain unchanged.

Use `seed-01@passit.demo` for a demo spanning lending and borrowing: an upcoming tent pickup, an upcoming projector rental, a drill due back, and completed rentals with reviews. The first three accounts also have saved listings. Two listings are paused to populate owner management.
