(() => {
  const message = document.querySelector("#raw-schedule-message");
  const date = document.querySelector("#raw-schedule-date");
  const clearButton = document.querySelector("#clear-schedule");
  const draft = document.querySelector("#schedule-draft");

  if (!message || !clearButton || !draft) return;

  const openEditor = (control, focusField = null) => {
    const target = document.getElementById(control.dataset.editTarget);
    if (!target) return;
    if (target.getAttribute("aria-hidden") === "true") return;
    target.hidden = false;
    target.classList.add("is-active-editor");
    if (focusField) {
      const field = target.querySelector(`[name="${focusField}"]`);
      if (field) {
        field.focus();
        if (typeof field.select === "function" && field.type !== "time") field.select();
      }
    }
  };

  document.querySelectorAll("button[data-edit-target], button.draft-cancel-button").forEach((button) => {
    button.addEventListener("click", () => {
      const target = document.getElementById(button.dataset.editTarget);
      if (!target) return;
      target.hidden = !target.hidden;
      if (!target.hidden) target.classList.add("is-active-editor");
    });
  });

  document.querySelectorAll(".draft-inline-editable[data-edit-target]").forEach((cell) => {
    cell.addEventListener("click", () => openEditor(cell, cell.dataset.inlineField));
    cell.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openEditor(cell, cell.dataset.inlineField);
      }
    });
    cell.tabIndex = 0;
  });

  clearButton.addEventListener("click", () => {
    window.setTimeout(() => {
      message.value = "";
      draft.hidden = true;
    }, 0);
    message.focus();
  });
})();
