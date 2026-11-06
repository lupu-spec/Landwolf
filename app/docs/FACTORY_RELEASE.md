# Factory releases

The factory RELEASE tab builds an approved result in Docker, tests a preview,
publishes the exact saved static files, checks the public site, and records an
explicit DELIVER decision. The linked customer request then shows the product
and authenticated source download when its workspace is refreshed.

Only registered local Cloudflare Pages static projects are supported initially.
Website requests cannot choose host commands, paths, credentials, or hosting
accounts. The calculator registration permits `content/copy.json`; its separate
browser specification and acceptance tests remain outside model control.

Versions are unique per project. The result ID, approval revision, selected files,
source package hash, and deployed asset manifest are retained. Expired jobs stop
visibly; retries reuse the operation identity. Publishing cannot rebuild or change
files after preview verification. A failed live check blocks delivery and attempts
to restore and verify the retained previous artifact. Explicit restoration also
requires the previous hash. A restored release needs a new version to publish again.

The portal synchronizes bounded delivery history independently of newer build attempts.
The portal records the factory's explicit delivery once, scoped to the immutable
request/dispatch/customer link. It does not infer ownership from email. Other
services remain open. Source downloads require the same customer session or an
owner session, verify package bytes, and use no-store responses. Private runner
reports, credentials and host paths are not exposed to customers.

Current limits: 30 releases per task, 500 public files, 500 KB compressed source
package, fixed Pages project and production URL. New projects need a locally
reviewed profile and acceptance/browser checks. No automatic billing or customer
email is added.

## Verification status

Production v0.23.1 is verified. The original calculator release 1.0.2 completed the
factory and portal delivery path, including the actual source download and reload.
Full source gates, hosted staging/production checks, customer isolation and a real
Cloudflare restoration rehearsal passed. See RELEASES.md and docs/VERIFICATION.md
for immutable runtime commits, deployments, commands, failed attempts and limits.
