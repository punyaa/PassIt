# PassIt demo script (draft)

Owner: F1. Target length: 8 minutes. Rehearse against the demo environment, not localhost.

## Before the demo

1. Reset data: `python -m scripts.seed --reset`. Keep the printed tokens for Aisha (lender), Ben (borrower) and Chloe (second borrower).
2. Set `PASSIT_FEE_HOLD_MINUTES=1` so the fee release happens live.
3. Open three browser profiles, one per person, each signed in with its demo session.
4. Have a phone ready for the handover photo, and keep a backup recording.

## Script

| Time | Who | Show | Say |
| --- | --- | --- | --- |
| 0:00 | Ben | Home → search "tent", filter by MRT and dates | Search only shows items that are free for your dates, near your MRT station. |
| 1:00 | Aisha | List an item → **Suggest prices** → publish | Pricing help comes from an LLM, with a fallback so listing never blocks. There's a three-listing free tier. |
| 2:30 | Ben | Open Aisha's item → pick dates → **Book now** | Fee and deposit are held in a double-entry ledger. |
| 3:00 | Chloe | Same item, overlapping dates | The dates show as booked. If both press Book at the same instant, the database constraint lets exactly one through (cite the contention results). |
| 3:45 | Ben (phone) | **Start handover**: take a photo, tick the checklist, confirm | Photos are write-once evidence. The fee-release countdown starts now. |
| 5:00 | Ben | **Record the return** with the handover photos alongside | |
| 5:45 | Aisha | **Report damage** → Moderate → outcome screen | Damage uses fixed tiers, not free-form claims: 40% of the deposit to the lender, the rest refunded. |
| 6:45 | Aisha | Booking page: "Rental fee released"; lender dashboard | Release is a scheduled job and idempotent: retries never pay twice. |
| 7:15 | Both | Reviews; borrower dashboard savings | |
| 7:45 | | Close on architecture and cost slide | |

## If something breaks

- Booking fails: switch to the backup recording at the same timestamp.
- Fee release slow: run `python -m scripts.release_due_fees` (idempotent) and refresh.
- Photo upload fails on the phone: use a laptop photo from `docs/demo-assets/` (add before rehearsal).
