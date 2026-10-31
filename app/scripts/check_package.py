"""Fail packaging if the deployable wheel omits the app or browser assets."""

from pathlib import Path
from tarfile import open as open_tar
from zipfile import ZipFile

wheels = sorted(Path("dist").glob("landwolf-*.whl"))
if not wheels:
    raise SystemExit("No LandWolf wheel found; run the production build")
with ZipFile(wheels[-1]) as wheel:
    names = set(wheel.namelist())
    if "landwolf/saved.py" in names:
        raise SystemExit("Wheel contains retired Saved implementation")
    required = {
        "landwolf/main.py",
        "landwolf/public_pages.py",
        "landwolf/commercial.py",
        "landwolf/craigslist_regions.py",
        "landwolf/static/assets/public-theme.js",
        "landwolf/static/assets/public.css",
        "landwolf/static/assets/landscape.webp",
        "landwolf/static/assets/landwolf-logo.webp",
        "landwolf/static/assets/no-photo-available.webp",
        "landwolf/crm.py",
        "landwolf/crm_core.py",
        "landwolf/locations.py",
        "landwolf/static/index.html",
        "landwolf/static/assets/app.js",
        "landwolf/static/assets/styles.css",
        "landwolf/static/assets/graphite.css",
        "landwolf/static/assets/theme-init.js",
        "landwolf/static/assets/leaflet.css",
        "landwolf/static/assets/landwolf-logo.jpg",
        "landwolf/static/assets/romulus.svg",
        "landwolf/static/assets/remus.svg",
        "landwolf/static/assets/landscape.jpg",
    }
    missing = required - names
    if missing:
        raise SystemExit("Wheel missing required assets: " + ", ".join(sorted(missing)))
sdists = sorted(Path("dist").glob("landwolf-*.tar.gz"))
if not sdists:
    raise SystemExit("No source archive found; run the production build")
with open_tar(sdists[-1], "r:gz") as archive:
    sources = {name.partition("/")[2] for name in archive.getnames()}
    required_sources = {
        "web/property-context.ts",
        "web/source-filter.ts",
        "tests/test_commercial.py",
        "tests/test_commercial_browser.py",
        "web/public-theme.ts",
        "web/assets/landscape.webp",
        "tests/test_public_pages.py",
        "tests/test_public_pages_browser.py",
        "tests/property-context.test.mjs",
        "web/source-health.ts",
        "web/source-list.ts",
        "web/coverage.ts",
        "web/dom.ts",
        "web/graphite.css",
        "web/theme.ts",
        "web/theme-init.ts",
        "web/theme-preference.ts",
        "tests/theme-preference.test.mjs",
        "tests/test_theme_browser.py",
        "tests/test_header_css_browser.py",
        "tests/source-health.test.mjs",
    }
    if required_sources - sources:
        raise SystemExit("Source archive missing scenario helpers or frontend tests")
print("Passed: wheel contains runtime/branding assets; source archive contains frontend tests")
