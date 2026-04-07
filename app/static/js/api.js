export function formToJson(form) {
  const data = new FormData(form);
  const json = Object.fromEntries(data.entries());
  const numericFields = [
    "procedural_stage",
    "sponsor_strength",
    "funding_clarity",
    "route_specificity",
    "need_case",
    "row_tractability",
    "local_plan_alignment",
    "opposition_drag",
    "land_monetization_fit",
  ];
  for (const field of numericFields) {
    if (json[field] !== undefined && json[field] !== "") {
      json[field] = Number(json[field]);
    }
  }
  return json;
}

export async function fetchJson(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(url, { ...options, headers, credentials: "same-origin" });
  const raw = await response.text();
  let payload;
  try {
    payload = raw ? JSON.parse(raw) : {};
  } catch {
    payload = { detail: raw || "Request failed" };
  }
  if (!response.ok) {
    throw new Error(payload.detail || "Request failed");
  }
  return payload;
}
