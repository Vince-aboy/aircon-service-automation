(() => {
  const message = document.querySelector("#raw-schedule-message");
  const date = document.querySelector("#raw-schedule-date");
  const clearButton = document.querySelector("#clear-schedule");
  const draft = document.querySelector("#schedule-draft");

  if (!message || !clearButton || !draft) return;

  clearButton.addEventListener("click", () => {
    window.setTimeout(() => {
      message.value = "";
      draft.hidden = true;
    }, 0);
    message.focus();
  });
})();
