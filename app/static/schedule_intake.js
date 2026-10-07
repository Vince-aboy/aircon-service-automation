(() => {
  const message = document.querySelector("#raw-schedule-message");
  const date = document.querySelector("#raw-schedule-date");
  const previewButton = document.querySelector("#preview-schedule");
  const clearButton = document.querySelector("#clear-schedule");
  const draft = document.querySelector("#schedule-draft");
  const rows = document.querySelector("#draft-schedule-rows");

  if (!message || !previewButton || !clearButton || !draft || !rows) return;

  const locationPattern = /\b(?:b|bldg|building)\s*(\d+)\s*,?\s*(?:unit\s*)?(\d+)\b/i;
  const timePattern = /^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$/i;
  const pricePattern = /^₱?\s*\d+(?:\.\d{2})?$/;

  function standardLocation(value) {
    const match = value.trim().match(locationPattern);
    return match ? `Building ${match[1]}, Unit ${match[2]}` : value.trim();
  }

  function standardTime(value) {
    const match = value.trim().match(timePattern);
    if (!match) return "";
    let hour = Number(match[1]);
    const minute = match[2] || "00";
    const meridiem = match[3].toUpperCase();
    if (meridiem === "PM" && hour < 12) hour += 12;
    if (meridiem === "AM" && hour === 12) hour = 0;
    return `${String(hour).padStart(2, "0")}:${minute}`;
  }

  function escapeHtml(value) {
    return value.replace(/[&<>'"]/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
    }[character]));
  }

  function parseMessage() {
    const lines = message.value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    const parsed = [];
    let current = null;

    lines.forEach((line) => {
      const location = line.match(locationPattern);
      const time = standardTime(line);
      const price = pricePattern.test(line) ? line.replace(/^₱\s*/, "₱") : "";
      const service = /cleaning|drainpan|check\s*up|checkup|greasetrap|back\s*job/i.test(line);

      if (location) {
        if (current) parsed.push(current);
        current = { location: standardLocation(line), service: "", time: "", price: "" };
      } else if (current && time) {
        current.time = time;
      } else if (current && price) {
        current.price = `₱${price.replace(/^₱\s*/, "")}`;
      } else if (current && service) {
        current.service = current.service ? `${current.service} + ${line}` : line;
      }
    });
    if (current) parsed.push(current);
    return parsed;
  }

  function renderDraft() {
    const parsed = parseMessage();
    if (!parsed.length) {
      rows.innerHTML = '<tr><td colspan="7" class="draft-empty">Paste a location and service to prepare a draft.</td></tr>';
    } else {
      rows.innerHTML = parsed.map((item) => {
        const missing = !item.time || !item.service;
        return `<tr>
          <td><span class="draft-missing">Missing</span></td>
          <td>${escapeHtml(item.location)}</td>
          <td><span class="draft-missing">Missing</span></td>
          <td>${escapeHtml(item.service || "Missing")}</td>
          <td>${item.time ? escapeHtml(item.time) : '<span class="draft-missing">Missing</span>'}</td>
          <td>${item.price ? escapeHtml(item.price) : '<span class="draft-missing">Missing</span>'}</td>
          <td><span class="draft-status ${missing ? "draft-status-warning" : "draft-status-ready"}">${missing ? "Needs review" : "Draft"}</span></td>
        </tr>`;
      }).join("");
    }
    draft.hidden = false;
    draft.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  previewButton.addEventListener("click", renderDraft);
  clearButton.addEventListener("click", () => {
    message.value = "";
    rows.innerHTML = "";
    draft.hidden = true;
    message.focus();
  });
})();
