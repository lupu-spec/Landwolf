# Public SEO boundary (v0.16.0 candidate)

The new public routes `/land-investing`, `/faq` and `/about` are server-rendered
product information for US land investors. The existing home and trial terms
also deliver their public content in the initial HTML response. Sign-in, research,
scenarios, billing and CRM retain their established security and module boundaries.
No public page reads account or property records. No database migration is needed.

`landwolf/public_pages.py` owns the public allowlist, sitemap, robots policy,
breadcrumb schema and visible FAQ questions/answers. Canonicals use the fixed
production origin `https://landwolf.ai`, never client headers. Only production
advertises sitemap URLs and permits public crawling. Staging retains global
noindex and disallow; its sitemap is empty. API responses carry noindex/nofollow.
Authentication, not robots.txt, remains the privacy boundary.

Every public page has a title, unique description and one H1. The home footer and
public navigation link every public route. Child pages have visible breadcrumbs;
new information pages also expose BreadcrumbList schema. FAQPage schema exactly
matches the visible FAQ. Google generally restricts FAQ rich results to authoritative
health/government sites; markup does not promise an enhanced result:
https://developers.google.com/search/docs/appearance/structured-data/faqpage

Unknown URLs retain genuine 404s. Trailing slash variants redirect once. The obsolete
version-history link now uses main. Do not hide arbitrary 404s behind a home redirect.
The deployed check verifies HTTP/apex and HTTPS/www redirects to the final canonical
origin. Redirect and external 404 audits remain unconfirmed until hosted checks run.

## Assets and speed

The supplied original images remain unchanged. WebP quality-90 derivatives are:
landscape 1920×1440 (719,434 bytes), logo 1536×512 (44,466 bytes), fallback photo
768×512 (76,420 bytes). The logo uses a picture source with the original JPEG fallback.
SVG icons stay SVG. Decorative icons keep empty alternative text; content images
retain descriptive alternatives. Source-owned external photos keep their original
URLs and attribution rather than introducing a new fetch/proxy trust boundary.

New public pages use a system font, small dedicated stylesheet, existing theme
initializer and a tiny public entry point reusing `setupAppearance`, with no Leaflet or application bundle. Image dimensions reserve layout
space. The public appearance selector persists Light/Dark/Auto and follows system changes live.
Browser tests capture Light, Dark and Auto at 390/834/1440 pixels in Chromium
and WebKit, assert computed colors and no overflow, verify no-JS navigation and save
screenshots plus navigation timing and CLS support/values. The local CI budget is
load <2 seconds and CLS ≤0.1. WebKit lacks layout-shift entries; zero entries there
are not a measured CLS result. A local budget is not proof of mobile field speed.
Measure deployed LCP, INP and CLS on representative devices/networks before claiming
that the whole application loads under two seconds.

## Search Console, authorship and links

Search Console requires the owner's authenticated verified property. Google sign-in
was requested through the secure browser flow but timed out. No submission, ownership
verification, indexing or ranking is confirmed. After deployment, submit the production
sitemap and inspect the home, checklist and FAQ URLs. Record the observed result.
A sitemap does not guarantee indexing or rankings:
https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap

The owner selected “Provide my bio”; the actual biography and credentials have not
been supplied. Product content is attributed to LandWolf / L91 LLC until confirmed
personal details arrive. Do not invent experience, credentials or testimonials.

The checklist is a useful resource for relevant editorial links. Suggested outreach
copy for an existing, owner-approved land-investing partner: “We published a land
purchase research checklist covering sale terms, parcel access, unanswered risks and
scenario costs. If it would help your readers, please consider citing it as a research
resource: https://landwolf.ai/land-investing.” Confirm the named recipient and copy
before sending. Track editorial fit, placement and observed inbound link separately.
No messages, paid placements, new provider accounts or backlinks were created here.
Do not buy ranking links, post unsolicited promotions or invent endorsements.

## Checks and release

`tests/test_public_pages.py` covers documents, links, metadata, schema, genuine 404s,
authentication and environment crawl policies. `tests/test_public_pages_browser.py`
saves responsive evidence to `test-results/public-seo/` and runs before the full
browser suite. All existing gates remain required. `scripts/check_public_seo.py
--environment staging|production` is a read-only deployed check, run by the existing
hosted acceptance workflow after identity and account journeys. Timing output contains
public paths/bytes only. See VERIFICATION.md for actual results and RELEASES.md for
observed deployments. A branch push is not deployment.
