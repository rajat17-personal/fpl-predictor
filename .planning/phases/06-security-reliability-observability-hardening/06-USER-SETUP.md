# Phase 6: User Setup Required

**Generated:** 2026-09-05
**Phase:** 06-security-reliability-observability-hardening
**Status:** Incomplete

Complete these items for REL-02's and OBS-03's "a failed run is noticed the same
day" guarantee to actually hold. Claude automated everything else this phase
promises (retry/backoff on the daily snapshot, per-step outcome accounting in
both cron scripts, a never-raising `ops.notify.report()` alerting spine, and
`scripts/verify_hardening.sh`/`scripts/preflight.sh` proving all of it against
a real booted process) -- these three items require a human on the host that
actually runs the pipeline, which Claude cannot reach from this session.

`crontab -l` on this host currently reports no crontab, and `data/snapshots/`
holds a single day (2026-08-31) -- the daily price snapshot is not running.
Installing the schedule is what turns this phase's alerting from wiring into
real coverage.

## Dashboard Configuration

- [ ] **Install the daily cron line**
  - Location: the WSL/VPS host that runs the pipeline (crontab for the user
    that should own this job)
  - Command: `30 2 * * * /home/sraja/fpl/scripts/daily.sh >> /home/sraja/fpl/data/cron.log 2>&1`
  - Or the equivalent systemd timer if you prefer that over cron
  - Confirm with: `crontab -l`

- [ ] **Install the weekly cron line**
  - Location: the same host
  - Command: `0 8 * * fri /home/sraja/fpl/scripts/weekly.sh >> /home/sraja/fpl/data/cron.log 2>&1`
  - Confirm with: `crontab -l`

- [ ] **Confirm the alert webhook is watched**
  - Location: repository root `.env` on that host (`FPL_ALERT_WEBHOOK`)
  - Point it at a notification channel you actually watch (a free
    ntfy.sh topic URL, a Discord channel webhook, or a Slack incoming
    webhook all work per `.env.example`)
  - Trigger one deliberate failure and confirm the alert arrives -- for
    example, temporarily rename the conda interpreter path in your shell
    and run `bash scripts/daily.sh`, then check the channel

## Verification

After completing setup, verify with:

```bash
crontab -l
# expect both the daily (30 2 * * *) and weekly (0 8 * * fri) lines present

python -m ops.notify --job daily --step manual-test --message "phase 6 wiring check"
# expect no exception, and (if FPL_ALERT_WEBHOOK is set) a notification on
# the channel you configured within a few seconds
```

Expected results:
- `crontab -l` lists both scheduled jobs.
- The manual test alert lands in the channel you actually watch.
- A deliberately broken `scripts/daily.sh` run still reports a failure alert
  the same day, not silently.

This is a claim about your attention, not something an automated gate can
verify (see `.planning/phases/06-security-reliability-observability-hardening/06-05-PLAN.md`'s
`<human-check>`) -- no CI or preflight gate can substitute for actually
watching the channel land a message.

---

**Once all items complete:** Mark status as "Complete" at top of file.
