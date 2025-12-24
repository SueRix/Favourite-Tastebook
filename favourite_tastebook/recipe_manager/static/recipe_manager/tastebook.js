(function () {
  function parseIds(csv) {
    if (!csv) return [];
    return csv
      .split(",")
      .map((s) => parseInt(String(s).trim(), 10))
      .filter((n) => Number.isFinite(n) && n > 0);
  }

  function updateQuery(mutator) {
    const url = new URL(window.location.href);
    mutator(url.searchParams);
    url.searchParams.delete("page");
    window.location.href = url.toString();
  }

  function toggleIngredient(id) {
    updateQuery((sp) => {
      const current = new Set(parseIds(sp.get("ingredients")));
      if (current.has(id)) current.delete(id);
      else current.add(id);

      const next = Array.from(current).sort((a, b) => a - b);
      if (next.length) sp.set("ingredients", next.join(","));
      else sp.delete("ingredients");
    });
  }

  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".js-ingredient-toggle");
    if (!btn) return;

    e.preventDefault();
    const id = parseInt(btn.dataset.id, 10);
    if (!Number.isFinite(id)) return;

    toggleIngredient(id);
  });

  const strictToggle = document.getElementById("strictToggle");
  if (strictToggle) {
    strictToggle.addEventListener("change", () => {
      updateQuery((sp) => {
        if (strictToggle.checked) sp.set("strict", "1");
        else sp.delete("strict");
      });
    });
  }

  const tastesToggle = document.getElementById("tastesToggle");
  if (tastesToggle) {
    tastesToggle.addEventListener("change", () => {
      updateQuery((sp) => {
        if (tastesToggle.checked) sp.set("use_tastes", "1");
        else sp.delete("use_tastes");
      });
    });
  }

  const categorySelect = document.querySelector(".filter-select");
  if (categorySelect && categorySelect.form) {
    categorySelect.addEventListener("change", () => categorySelect.form.submit());
  }
})();
