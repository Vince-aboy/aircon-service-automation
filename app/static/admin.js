document.querySelectorAll("form[data-confirm]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (form.dataset.submitted === "true") {
      event.preventDefault();
      return;
    }
    if (!window.confirm(form.dataset.confirm)) {
      event.preventDefault();
      return;
    }
    form.dataset.submitted = "true";
    form.classList.add("is-submitting");
  });
});

document.querySelectorAll("form[data-lock-submit]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (form.dataset.submitted === "true") {
      event.preventDefault();
      return;
    }
    form.dataset.submitted = "true";
    form.classList.add("is-submitting");
  });
});

const adminShell = document.querySelector("#admin-shell");
const sidebarToggle = document.querySelector("#sidebar-toggle");

if (adminShell && sidebarToggle) {
  const toggleLabel = sidebarToggle.querySelector(".sidebar-toggle-label");
  const setSidebarCollapsed = (collapsed) => {
    adminShell.classList.toggle("sidebar-collapsed", collapsed);
    sidebarToggle.setAttribute("aria-expanded", String(!collapsed));
    sidebarToggle.title = collapsed ? "Show navigation menu" : "Hide navigation menu";
    if (toggleLabel) {
      toggleLabel.textContent = collapsed ? "Show menu" : "Hide menu";
    }
  };

  try {
    setSidebarCollapsed(window.localStorage.getItem("balik-lamig-sidebar-collapsed") === "true");
  } catch (_) {
    setSidebarCollapsed(false);
  }

  sidebarToggle.addEventListener("click", () => {
    const collapsed = !adminShell.classList.contains("sidebar-collapsed");
    setSidebarCollapsed(collapsed);
    try {
      window.localStorage.setItem("balik-lamig-sidebar-collapsed", String(collapsed));
    } catch (_) {
      // The layout still works if the browser blocks local storage.
    }
  });
}
