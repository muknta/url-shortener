function getCsrfToken() {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : "";
}

async function apiFetch(path, options = {}) {
  const defaults = {
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
      ...options.headers,
    },
  };
  const response = await fetch(path, { ...defaults, ...options, headers: defaults.headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const err = new Error(body.error || `HTTP ${response.status}`);
    err.status = response.status;
    throw err;
  }
  return response.json();
}

export function shortenUrl(url) {
  return apiFetch("/api/shorten/", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export function fetchPublicUrls() {
  return apiFetch("/api/urls/public/");
}

export function fetchMyUrls() {
  return apiFetch("/api/urls/mine/");
}
