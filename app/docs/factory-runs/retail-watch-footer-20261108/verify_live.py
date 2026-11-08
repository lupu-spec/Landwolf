import hashlib
import json
import sys
import time
import urllib.request
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

origin, environment, commit, output = sys.argv[1:]
started = datetime.now(UTC).isoformat()
tick = time.monotonic()


def fetch(path):
    with urllib.request.urlopen(origin + path, timeout=30) as response:
        assert response.status == 200
        assert response.url.startswith("https://")
        return response.read()


class FooterParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_footer = False
        self.links = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == "footer":
            self.in_footer = True
        if self.in_footer and tag == "a":
            self.current = dict(attrs)
            self.current["label"] = ""

    def handle_data(self, data):
        if self.current is not None:
            self.current["label"] += data

    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None:
            self.current["label"] = self.current["label"].strip()
            self.links.append(self.current)
            self.current = None
        if tag == "footer":
            self.in_footer = False


identity = json.loads(fetch("/api/version"))
health = json.loads(fetch("/api/health"))
assert identity == {"version": "0.24.2", "environment": environment, "commit": commit}, identity
assert health["status"] == "ok" and health["version"] == "0.24.2", health
assert health["payments_enabled"] == (environment == "production")
if environment == "production":
    with urllib.request.urlopen("https://www.landwolf.ai/api/version", timeout=30) as response:
        assert response.status == 200
        assert json.loads(response.read()) == identity
html = fetch("/")
parser = FooterParser()
parser.feed(html.decode())
selected = []
for name, url in [
    ("Audit Desk ↗", "https://l91-audit-desk.secret-hen-4327.chatgpt.site"),
    ("Retail Watch", "https://lupu-retail-watch.secret-hen-4327.chatgpt.site"),
]:
    links = [link for link in parser.links if link.get("href") == url]
    assert len(links) == 1, links
    link = links[0]
    assert link["label"] == name and link["target"] == "_blank", link
    assert set(link["rel"].split()) == {"noopener", "noreferrer"}, link
    selected.append(link)
assert b"OAI-Sites-Authorization" not in html and b"Bearer " not in html
assets = {}
for name in ["landwolf-logo.jpg", "no-photo-available.png"]:
    assets[name] = hashlib.sha256(fetch("/assets/" + name)).hexdigest()
    expected = Path("app/web/assets") / name
    assert assets[name] == hashlib.sha256(expected.read_bytes()).hexdigest()
result = {
    "startedAt": started,
    "completedAt": datetime.now(UTC).isoformat(),
    "durationSeconds": time.monotonic() - tick,
    "origin": origin,
    "identity": identity,
    "health": health,
    "footerLinks": selected,
    "htmlSha256": hashlib.sha256(html).hexdigest(),
    "assetSha256": assets,
    "scope": "Read-only HTTPS and returned markup; no computed-layout or physical-device claim",
    "result": "PASSED",
}
Path(output).write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
