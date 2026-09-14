"""Fail packaging if the deployable wheel omits the app or browser assets."""

from pathlib import Path
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
print("Passed: deployable wheel contains the app, original logo, and browser assets")
