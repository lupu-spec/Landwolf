/** Customer-safe release links. Source files remain behind the portal session. */
import { element } from "./dom";
export type Delivery = {
  id: string;
  version: string;
  url: string;
  source_url: string;
  checks: string;
};
export function releaseCards(releases: Delivery[], owner = false): HTMLElement {
  const section = element("section", "customer-management");
  if (!releases.length) return section;
  section.append(element("h3", "", "RELEASES"));
  for (const release of releases) {
    const card = element("article", "message");
    card.append(
      element("h4", "", "VERSION " + release.version),
      element("p", "note", "CHECKS " + release.checks),
    );
    const product = element("a", "button", "OPEN PRODUCT");
    product.href = release.url;
    product.target = "_blank";
    product.rel = "noopener noreferrer";
    const source = element("a", "button", "DOWNLOAD SOURCE");
    source.href = owner
      ? release.source_url.replace("/api/portal/", "/api/admin/portal/")
      : release.source_url;
    card.append(product, source);
    section.append(card);
  }
  return section;
}
