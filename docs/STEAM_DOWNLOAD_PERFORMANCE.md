# Steam download performance

## Baseline and measurement

The current downloader schedules up to eight chunks per depot with a shared
ephemeral `URLSession` and up to eight connections per host. It writes each
verified chunk with `pwrite` at the manifest offset, journals completed chunks,
and resumes an interrupted install. Network requests are therefore already
concurrent. There is no measured device throughput baseline yet, so increasing
the limit would be speculation.

Each completed depot now emits one `[steam-depot] timing` line. `fetched-bytes`
counts actual response bytes on successful chunk attempts, excluding journaled
or locally verified chunks. `wall` is monotonic elapsed time for that depot's
chunk phase; `MiBps` is fetched bytes divided by wall. `network-sum`,
`decode-sum`, and `write-sum` add the durations of successful chunk attempts.
Those sums overlap across parallel tasks and need not add up to `wall`.
`hosts` counts successful chunks per hostname; authentication query strings
are never logged. `retries` counts failed attempts before successful chunks.
Failures that ultimately abort the depot remain visible in the existing
per-attempt trace but have no completion line. This is a first measurement
point, not a complete URLSession transaction trace: connection setup,
time-to-first-byte, hash time and CPU load are not yet separately recorded.

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
