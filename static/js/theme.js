(function () {
  const saved = localStorage.getItem("quizora-theme") || "aurora";
  document.documentElement.setAttribute("data-theme", saved);
  function mark(t) {
    document.querySelectorAll("[data-theme-btn]").forEach(b =>
      b.classList.toggle("active", b.dataset.themeBtn === t));
  }
  document.addEventListener("DOMContentLoaded", () => {
    mark(saved);
    document.querySelectorAll("[data-theme-btn]").forEach(b => b.addEventListener("click", () => {
      document.documentElement.setAttribute("data-theme", b.dataset.themeBtn);
      localStorage.setItem("quizora-theme", b.dataset.themeBtn);
      mark(b.dataset.themeBtn);
    }));
  });
})();
