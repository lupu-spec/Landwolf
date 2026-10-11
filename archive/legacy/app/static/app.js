const $ = id => document.getElementById(id);

async function api(path, options={}) {
  options.credentials = "same-origin";
  options.headers = {...(options.headers || {}), "Content-Type":"application/json"};
  const response = await fetch(path, options);
  let data = {};
  try { data = await response.json(); } catch {}
  if (!response.ok) {
    const error = new Error(data.detail?.message || data.detail || "Request failed");
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
}

async function register() {
  try {
    await api("/api/auth/register", {
      method:"POST",
      body:JSON.stringify({email:$("email").value,password:$("password").value})
    });
    await refresh();
  } catch(e) { $("auth-message").textContent = e.message; }
}

async function login() {
  try {
    await api("/api/auth/login", {
      method:"POST",
      body:JSON.stringify({email:$("email").value,password:$("password").value})
    });
    await refresh();
  } catch(e) { $("auth-message").textContent = e.message; }
}

let currentSubscriptionStatus = "none";

async function refresh() {
  try {
    const me = await api("/api/auth/me");
    $("auth-card").classList.add("hidden");
    $("account").textContent = me.email;
    currentSubscriptionStatus = me.subscription_status || "none";
    const paid = ["active", "trialing"].includes(currentSubscriptionStatus);
    $("search-card").classList.remove("hidden");
    $("subscribe-card").classList.toggle("hidden", paid);
    $("access-status").textContent = paid
      ? "Subscription active — property-level intelligence and analysis unlocked"
      : "Opportunity Preview — see the strength of the search, then subscribe to investigate the properties behind it";
  } catch {
    currentSubscriptionStatus = "none";
    $("auth-card").classList.remove("hidden");
    $("search-card").classList.add("hidden");
    $("subscribe-card").classList.add("hidden");
  }
}

async function searchProperties() {
  $("search-message").textContent = "";
  $("preview-note").textContent = "";
  try {
    const params = {};
    ["city","state","county","distress_type"].forEach(k => {
      if ($(k).value) params[k] = $(k).value;
    });
    ["min_acres","max_price"].forEach(k => {
      if ($(k).value) params[k] = Number($(k).value);
    });

    if (["active", "trialing"].includes(currentSubscriptionStatus)) {
      const data = await api("/api/search", {method:"POST", body:JSON.stringify(params)});
      renderResults(data.results);
      return;
    }

    const preview = await api("/api/search/preview", {method:"POST", body:JSON.stringify(params)});
    renderPreview(preview);
    $("subscribe-card").classList.remove("hidden");
  } catch(e) {
    $("search-message").textContent = e.message;
  }
}

function renderPreview(p) {
  const categories = (p.category_summary || []).map(x => `<li>${escapeHtml(x)}</li>`).join("");
  $("results").innerHTML = `
    <div class="property preview-result">
      <strong>${escapeHtml(p.opportunity_signal)}</strong>
      <span class="badge">${p.match_count} potential match${p.match_count === 1 ? "" : "es"}</span>
      ${p.acreage_band ? `<div>Opportunity acreage range: ${escapeHtml(p.acreage_band)}</div>` : ""}
      ${p.value_band ? `<div>Estimated value range: ${escapeHtml(p.value_band)}</div>` : ""}
      ${categories ? `<div><strong>Top categories</strong><ul>${categories}</ul></div>` : ""}
      <div>${escapeHtml(p.message)}</div>
    </div>`;
  $("preview-note").textContent =
    "This preview summarizes the opportunity landscape without identifying individual properties. Subscribe to investigate and compare the underlying opportunities.";
}

function renderResults(rows) {
  $("results").innerHTML = rows.length ? rows.map(p => `
    <div class="property">
      <strong>${escapeHtml(p.address || "No address")}</strong>
      <span class="badge">${escapeHtml(p.distress_type || "market")}</span>
      <div>${escapeHtml([p.city,p.state,p.zip_code].filter(Boolean).join(", "))}</div>
      <div>${p.acreage ?? "—"} acres · estimated value $${p.estimated_value?.toLocaleString() ?? "—"} · data quality ${p.data_quality}</div>
    </div>
  `).join("") : "<p>No matching properties.</p>";
}

async function subscribe(plan) {
  try {
    $("billing-message").textContent = "Opening secure Stripe Checkout…";
    const data = await api("/api/billing/checkout", {
      method:"POST",
      body:JSON.stringify({plan})
    });
    location.href = data.checkout_url;
  } catch(e) { $("billing-message").textContent = e.message; }
}

async function logout() {
  try { await api("/api/auth/logout", {method:"POST"}); } catch {}
  $("account").textContent = "";
  refresh();
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
}


function showCheckoutResult() {
  const params = new URLSearchParams(window.location.search);
  const result = params.get("checkout");
  if (!result) return;

  const message = $("billing-message");
  if (result === "success") {
    message.textContent = "Payment received. Activating your LandWolf subscription…";
    // Webhooks are authoritative. Refresh account state shortly after returning
    // from Stripe to pick up the subscription lifecycle event.
    setTimeout(refresh, 1500);
    setTimeout(refresh, 4000);
  } else if (result === "cancel") {
    message.textContent = "Checkout was canceled. No subscription changes were made.";
  }

  const cleanUrl = new URL(window.location.href);
  cleanUrl.searchParams.delete("checkout");
  window.history.replaceState({}, "", cleanUrl.pathname + cleanUrl.search + cleanUrl.hash);
}

refresh();
showCheckoutResult();

const copyrightYear = document.getElementById("copyright-year");
if (copyrightYear) {
  copyrightYear.textContent = new Date().getFullYear();
}
