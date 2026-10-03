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
