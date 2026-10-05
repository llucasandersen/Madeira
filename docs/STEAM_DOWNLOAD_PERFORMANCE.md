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

## Measurement report tool

Use `python tools/depot-benchmark-report.py trial-1.txt trial-2.txt trial-3.txt`
to summarize the recorded timings. Supply one log containing one install trial
per file, with the same workload and fresh/resumed state across trials. Repeated
depot IDs are rejected so multiple installs cannot silently become one trial.
Fully resumed depots with no fetched bytes are excluded from network samples.
The tool accepts both the original aggregate timing and the later stage split.

For an optional control comparison, add `--control control.json`. The file is
a JSON array of native URLSession response measurements, for example:

```json
[{"bytes": 104857600, "seconds": 10.0},
 {"bytes": 104857600, "seconds": 11.0},
 {"bytes": 104857600, "seconds": 9.5}]
```

These example numbers are illustrative, not measured results. Record actual
response bytes and elapsed seconds from the same phone/network/CDN before
using the comparison. The report calculates each trial's rate from bytes and
summed depot chunk-phase wall time, then compares median rates with the 70%
target. It does not trust the rounded `MiBps` field, run the control transfer,
or establish a speed improvement by itself. Payload includes retried responses,
so a high payload rate with corruption/retries does not prove useful installed
throughput. Manifest acquisition, resume checks, finalization and failed depots
are outside this completion metric; retain the progress timeline and failure
report for the full install comparison. Stage sums overlap across chunks.

The tool reads files without modifying game content and emits selected numeric
fields only, excluding raw log lines, CDN URLs and authorization strings. It
does not replace the device benchmark or the missing URLSession transaction
instrumentation described above.

The decoder timing extension passed the complete 59-check host suite in
[run 37236100223](https://github.com/llucasandersen/Madeira/actions/runs/37236100223)
at `c76fd42`, including the production depot/decoder harness under
AddressSanitizer. This verifies host regression behavior, not phone throughput.

## URLSession transaction extension

The source now attaches a shared, locked per-depot metrics delegate to chunk
requests through Apple's
[`data(from:delegate:)`](https://developer.apple.com/documentation/foundation/urlsession/data(from:delegate:)).
It retains only numeric measurements and hostnames, never full request URLs,
headers or CDN authorization fragments. Each depot reports request completion
and metrics callback counts, plus observed peak active requests and chunks.
Host summaries include transaction/status/protocol counts, connection reuse,
response body bytes, DNS, connection, TLS and first-response-byte durations.

Durations are summed per host and include the number of usable samples.
`unavailable` denotes no sample, including TLS on HTTP or connection setup on
reused connections; it does not assert that setup took zero time. These
fields come from
[`URLSessionTaskTransactionMetrics`](https://developer.apple.com/documentation/foundation/urlsessiontasktransactionmetrics).
TTFB is measured from `fetchStartDate` to `responseStartDate`, including setup.
Connection/TLS/TTFB intervals can overlap, so they must not be added as
disjoint work. Host timing covers observed callbacks for chunk HTTP attempts,
including HTTP errors and retries, and is emitted on depot failure as well as
success. Manifests and authorization requests are outside this measurement.
Compare callback counts with requests before assuming complete coverage on
any Foundation backend.

The new macOS fixture uses the production HTTP helper and delegate against a
delayed localhost server, with both success and HTTP-error responses. The full
host suite now has 60 checks: the existing 59 plus this Apple metrics fixture.
Its first CI run and a new iOS compile are pending. This extension is not in
the already delivered `e6f6a2c` diagnostic IPA. CPU load, resume SHA-1 timing,
adaptive concurrency and a measured native control benchmark remain required.
