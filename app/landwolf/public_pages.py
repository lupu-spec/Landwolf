"""Public search documents, deliberately independent of private application data."""

import json
from collections.abc import Callable
from html import escape

from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, RedirectResponse

from landwolf.config import Settings

ORIGIN = "https://landwolf.ai"
FAQ = (
    (
        "What does LandWolf help me research?",
        "LandWolf brings connected official sale inventories, property research and user-entered "
        "deal scenarios into one workspace. Coverage and freshness vary by source. "
        "Verify sale terms with the originating agency.",
    ),
    (
        "Does LandWolf cover every parcel in the United States?",
        "No. You can search across all 50 states, but connected sources do not cover every county "
        "or parcel. A missing listing or unavailable record does not mean a property is risk-free.",
    ),
    (
        "Are scenario results appraisals?",
        "No. Scenarios use your inputs and explicitly labeled assumptions. "
        "They are not appraisals, "
        "resale predictions, or investment, legal or tax advice. Verify unknown costs "
        "independently.",
    ),
    (
        "Does creating an account start billing?",
        "No. Standard memberships cost $29 per month or $299 per year. Invited pilots and "
        "complimentary accounts have separate terms. Optional feedback trials require separate "
        "consent. Read the full trial terms before enrolling.",
    ),
)
PAGES = {
    "/land-investing": (
        "Land investing research checklist",
        "Research US land purchases with a checklist for official sale terms, parcel access, "
        "title, flood risk and deal assumptions using LandWolf.",
        """<p>Before bidding on land, establish what is being sold, which records support the
 description, and what remains unknown. LandWolf helps organize this research. It does not
 replace the agency, title professional or local authority responsible for a record.</p>
<h2>Start with the official sale record</h2>
<p>Confirm the sale status, deadline, deposit, buyer eligibility and payment terms with the
 originating agency. Check when the listing was retrieved. A cached listing is not confirmation
 that a sale remains open.</p>
<h2>Identify the parcel and access</h2>
<p>Match the legal description and parcel identifier against county records. Distinguish
 approximate map locations from verified parcel coordinates. Ask the relevant authority about
 recorded access, permitted uses, utilities and development restrictions.</p>
<h2>Document risks and unanswered questions</h2>
<p>Review available flood, environmental and public-record references. Missing data is an
 unanswered question. Record the source, date and follow-up needed. Obtain qualified title
 and legal review where appropriate.</p>
<h2>Build scenarios from explicit inputs</h2>
<p>Separate the asking price from your bid and any resale assumption. Include acquisition,
 holding, improvement and selling costs. Zero cost placeholders can overstate returns.
 Compare scenarios and keep a record of what you assumed.</p>
<h2>Keep your research connected</h2>
<p>Inside LandWolf, use property research, Hunts and private decision notes to track the
 questions behind a potential purchase. Source coverage varies. Check original records
 before acting.</p><p>Product information by LandWolf, operated by L91 LLC.</p>""",
    ),
    "/faq": (
        "LandWolf frequently asked questions",
        "Learn about LandWolf’s official-source land research, US coverage limits, "
        "deal scenario assumptions, account access and membership terms.",
        "".join(f"<h2>{escape(q)}</h2><p>{escape(a)}</p>" for q, a in FAQ)
        + '<p><a href="/trial-terms">Read the full feedback trial terms</a>.</p>',
    ),
    "/about": (
        "About LandWolf",
        "LandWolf is operated by L91 LLC and helps US land investors organize official-source "
        "listings, property research and transparent deal scenarios.",
        """<p>LandWolf is operated by L91 LLC. It helps people researching US land purchases
 organize connected official-source listings, public-record references and private deal
 scenarios.</p><h2>How information is presented</h2>
<p>Listings retain source attribution. Coverage varies by agency and location. Missing values
 stay unknown, and user-entered scenario assumptions are distinct from verified facts.
 Verify records and sale terms with the original source before making a decision.</p>
<h2>Contact</h2><p>For product questions, account help or corrections, email
<a href="mailto:support.landwolf@gmail.com">support.landwolf@gmail.com</a>.
 Do not send passwords or payment card details.</p>""",
    ),
}


def render_home(source: str, *, trial_enabled: bool) -> str:
    """Render only the already-public availability flag, never account/session data."""
    marker = 'id="trial-signup-offer" hidden'
    if source.count(marker) != 1:
        raise ValueError("Home template must contain one trial-offer visibility marker")
    return source.replace(marker, 'id="trial-signup-offer"' if trial_enabled else marker)


def document(path: str) -> str:
    title, description, body = PAGES[path]
    data: list[dict[str, object]] = [
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "LandWolf", "item": ORIGIN + "/"},
                {"@type": "ListItem", "position": 2, "name": title, "item": ORIGIN + path},
            ],
        }
    ]
    if path == "/faq":
        data.append(
            {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a},
                    }
                    for q, a in FAQ
                ],
            }
        )
    links = (
        '<a href="/">Sign in</a>'
        + "".join(f'<a href="{url}">{escape(values[0])}</a>' for url, values in PAGES.items())
        + '<a href="/trial-terms">Trial terms</a>'
    )
    structured = json.dumps(data, ensure_ascii=True).replace("<", "\\u003c")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} | LandWolf</title>
<meta name="description" content="{escape(description, quote=True)}">
<link rel="canonical" href="{ORIGIN}{path}"><link rel="icon" href="/favicon.svg">
<script src="/assets/theme-init.js"></script><link rel="stylesheet" href="/assets/public.css">
<script defer src="/assets/public-theme.js"></script>
<script type="application/ld+json">{structured}</script></head><body>
<a class="skip-link" href="#main">Skip to content</a><header>
<a href="/" aria-label="LandWolf home">
<img src="/assets/landwolf-logo.webp" width="270" height="90" alt="LandWolf"></a>
<nav aria-label="Public navigation">{links}</nav>
<label>Appearance <select id="appearance" aria-label="Appearance">
<option value="system">Auto</option><option value="light">Light</option>
<option value="dark">Dark</option></select></label></header><main id="main">
<nav aria-label="Breadcrumb"><a href="/">LandWolf</a> /
<span aria-current="page">{escape(title)}</span></nav><h1>{escape(title)}</h1>{body}</main>
<footer>© L91 LLC · LandWolf. Verify records with their original source.</footer></body></html>'''


def page_handler(path: str) -> Callable[[], HTMLResponse]:
    def render() -> HTMLResponse:
        return HTMLResponse(document(path))

    return render


def canonical_redirect(path: str) -> Callable[[], RedirectResponse]:
    def redirect() -> RedirectResponse:
        # Relative URLs retain HTTPS behind Render without trusting forwarding headers.
        return RedirectResponse(path, status_code=308)

    return redirect


def register(app: FastAPI, settings: Settings) -> None:
    for path in PAGES:
        app.add_api_route(path, page_handler(path), methods=["GET"], include_in_schema=False)

    for path in (*PAGES, "/trial-terms"):
        app.add_api_route(
            path + "/", canonical_redirect(path), methods=["GET"], include_in_schema=False
        )

    @app.get("/robots.txt", include_in_schema=False)
    def robots() -> Response:
        body = "User-agent: *\nDisallow: /\n"
        if settings.environment == "production":
            body = f"User-agent: *\nAllow: /\nDisallow: /api/\nSitemap: {ORIGIN}/sitemap.xml\n"
        return Response(body, media_type="text/plain")

    @app.get("/sitemap.xml", include_in_schema=False)
    def sitemap() -> Response:
        paths = ("/", *PAGES, "/trial-terms") if settings.environment == "production" else ()
        urls = "".join(f"<url><loc>{ORIGIN}{path}</loc></url>" for path in paths)
        return Response(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + urls + "</urlset>",
            media_type="application/xml",
        )
