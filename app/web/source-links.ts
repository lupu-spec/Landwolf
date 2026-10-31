/** Display-only source links. Fetch authorization remains stricter on the server. */
import { element } from "./dom";

export function sourceLink(url: string, label: string): HTMLAnchorElement {
  const a = element("a", "", label);
  try {
    const parsed = new URL(url);
    if (
      parsed.protocol === "https:" &&
      !parsed.username &&
      !parsed.password &&
      !parsed.port &&
      [
        "www.glo.texas.gov",
        "www.zillow.com",
        "www.craigslist.org",
        "www.compass.com",
        "www.resales.usda.gov",
        "www.irsauctions.gov",
        "www.treasury.gov",
        "dnr.alaska.gov",
        "www.dnr.state.mi.us",
        "www.michigan.gov",
        "www.hudhomestore.gov",
        "disposal.gsa.gov",
        "www.usa.gov",
        "cosl.org",
        "geocoding.geo.census.gov",
        "www.fema.gov",
        "epqs.nationalmap.gov",
        "sdmdataaccess.nrcs.usda.gov",
        "www.nconemap.gov",
        "www.dot.state.mn.us",
        "edocs-public.dot.state.mn.us",
        "www.dnr.state.mn.us",
        "land.az.gov",
      ].includes(parsed.hostname)
    )
      a.href = url;
  } catch {
    /* A malformed source is displayed without an actionable URL. */
  }
  a.target = "_blank";
  a.rel = "noopener noreferrer";
  return a;
}
