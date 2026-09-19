"""Fail packaging if the deployable wheel omits the app or browser assets."""

from pathlib import Path
from tarfile import open as open_tar
from zipfile import ZipFile

wheels = sorted(Path("dist").glob("landwolf_beta-*.whl"))
if not wheels:
    raise SystemExit("No LandWolf wheel found; run the production build")
with ZipFile(wheels[-1]) as wheel:
    names = set(wheel.namelist())
    required = {
        "landwolf/main.py",
        "landwolf/static/index.html",
        "landwolf/static/assets/app.js",
        "landwolf/static/assets/styles.css",
        "landwolf/static/assets/leaflet.css",
        "landwolf/static/assets/landwolf-logo.png",
        "landwolf/static/assets/landscape.jpg",
    }
    missing = required - names
    if missing:
        raise SystemExit("Wheel missing required assets: " + ", ".join(sorted(missing)))
sdists = sorted(Path("dist").glob("landwolf_beta-*.tar.gz"))
if not sdists:
    raise SystemExit("No source archive found; run the production build")
with open_tar(sdists[-1], "r:gz") as archive:
    sources = {name.partition("/")[2] for name in archive.getnames()}
    required_sources = {"web/property-context.ts", "tests/property-context.test.mjs"}
    if required_sources - sources:
        raise SystemExit("Source archive missing scenario helpers or frontend tests")
print("Passed: wheel contains runtime/branding assets; source archive contains frontend tests")
