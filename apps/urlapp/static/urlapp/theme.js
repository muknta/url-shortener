document.addEventListener("DOMContentLoaded", function () {
  var toggle = document.getElementById("theme-toggle");
  if (!toggle) return;

  function getTheme() {
    return document.documentElement.getAttribute("data-bs-theme") || "light";
  }

  function updateToggleIcon(theme) {
    if (theme === "dark") {
      toggle.innerHTML = '<i class="fas fa-sun"></i>';
      toggle.setAttribute("aria-label", "Switch to light mode");
    } else {
      toggle.innerHTML = '<i class="fas fa-moon"></i>';
      toggle.setAttribute("aria-label", "Switch to dark mode");
    }
  }

  function setTheme(theme) {
    document.documentElement.setAttribute("data-bs-theme", theme);
    localStorage.setItem("theme", theme);
    updateToggleIcon(theme);
  }

  // Reflect the current theme (already applied before paint by the inline snippet)
  updateToggleIcon(getTheme());

  toggle.addEventListener("click", function () {
    var current = getTheme();
    setTheme(current === "dark" ? "light" : "dark");
  });
});
