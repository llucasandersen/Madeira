# Steam download performance

## Baseline and measurement

The current downloader schedules up to eight chunks per depot with a shared
ephemeral `URLSession` and up to eight connections per host. It writes each
verified chunk with `pwrite` at the manifest offset, journals completed chunks,
and resumes an interrupted install. Network requests are therefore already
concurrent. There is no measured device throughput baseline yet, so increasing
the limit would be speculation.

Each completed depot now emits one `[steam-depot] timing` line. `fetched-bytes`
counts downloaded payload bytes, including responses retried after decode or
checksum failures, excluding journaled or locally verified chunks. HTTP errors
that the download helper throws do not return a payload to this counter.
`wall` is monotonic elapsed time for that depot's
chunk phase; `MiBps` is fetched bytes divided by wall. `network-sum`,
`decode-sum`, and `write-sum` add the durations of chunk attempts, including
failed attempts before eventual success. `decrypt-sum`, `decompress-sum` and
`checksum-sum` split the decode pipeline into its three stages. The checksum
stage measures the existing Adler-32 validation; local resume verification's
SHA-1 time is not included. A stage records elapsed time even when it throws.
Those sums overlap across parallel tasks and need not add up to `wall`.
`hosts` counts successful chunks per hostname; authentication query strings
are never logged. `retries` counts failed attempts before successful chunks.
Failures that ultimately abort the depot remain visible in the existing
per-attempt trace but have no completion line. This is a first measurement
point, not a complete URLSession transaction trace: connection setup,
time-to-first-byte, local resume SHA-1 time and CPU load are not yet separately
recorded. Build attempts dispatched before this extension use the earlier
aggregate timing; match the source commit to the log
fields when comparing measurements.

## Device benchmark protocol

1. On the same phone, network and Steam account, record the iOS version,
   available space, selected app and depot IDs, and whether the install is
   fresh or resumed. Keep credentials and CDN authorization strings out of
   the report.
2. Download a large owned game with Madeira. Save the progress timeline,
   `[steam-depot] timing` lines, failure traces, and iOS memory/CPU sample.
   Repeat three times after removing only that game's downloaded content and
   journal. Record CDN hosts, average and median `MiBps`, retries and the
   network/decode/write sums for each depot.
3. Measure a direct native `URLSession` control transfer from a comparable
   Steam CDN response on the same network and phone. Use an authorized public
   object or a chunk for which the account has authorization; redact its
   token. Record response bytes and wall time. Do not use the control to
   bypass Steam ownership or alter game files.
4. Compare the medians. The target is roughly 70% of the control median when
   CPU and decode are not limiting. Use the stage timings and host failures
   before changing concurrency or server rotation. Re-run interrupted resume,
   update, corruption and ownership tests after any downloader change.

No phone benchmark or improvement claim has been made for this fork yet.

The decoder timing extension passed the complete 59-check host suite in
[run 37236100223](https://github.com/llucasandersen/Madeira/actions/runs/37236100223)
at `c76fd42`, including the production depot/decoder harness under
AddressSanitizer. This verifies host regression behavior, not phone throughput.
