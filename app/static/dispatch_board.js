const modal = document.querySelector("#job-detail-modal");
const content = document.querySelector("#job-detail-content");
const closeButton = document.querySelector(".modal-close");

document.querySelectorAll(".scheduled-card[data-detail-url]").forEach((card) => {
  card.addEventListener("click", async (event) => {
    event.preventDefault();
    try {
      const response = await fetch(card.dataset.detailUrl, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      if (!response.ok) throw new Error("Job details are unavailable.");
      content.innerHTML = await response.text();
      modal.showModal();
    } catch {
      window.location.href = card.href;
    }
  });
});

closeButton.addEventListener("click", () => modal.close());
modal.addEventListener("click", (event) => {
  if (event.target === modal) modal.close();
});
