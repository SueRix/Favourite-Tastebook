(function () {
  /* =========================
     Helpers
  ========================= */
  function emitFiltersChanged() {
    document.body.dispatchEvent(
      new Event("ft:filtersChanged", { bubbles: true })
    );
  }

  function formEl() {
    return document.getElementById("filters-form");
  }

  /* =========================
     Hidden ingredients logic
  ========================= */
  function hasHiddenIngredient(id) {
    return !!document.querySelector(
      `#filters-form input[name="ingredient"][value="${id}"]`
    );
  }

  function addHiddenIngredient(id) {
    const f = formEl();
    if (!f || hasHiddenIngredient(id)) return;

    const inp = document.createElement("input");
    inp.type = "hidden";
    inp.name = "ingredient";
    inp.value = String(id);
    inp.setAttribute("data-ingredient-hidden", String(id));
    f.appendChild(inp);
  }

  function removeHiddenIngredient(id) {
    document
      .querySelectorAll(
        `#filters-form input[name="ingredient"][value="${id}"]`
      )
      .forEach((n) => n.remove());
  }

  function toggleIngredient(id) {
    if (hasHiddenIngredient(id)) {
      removeHiddenIngredient(id);
    } else {
      addHiddenIngredient(id);
    }
    emitFiltersChanged();
  }

  /* =========================
     Click handlers
     (ВАЖНО: preventDefault)
  ========================= */
  function bootIngredientHandlers() {
    document.addEventListener("click", (e) => {
      const pill = e.target.closest?.(".pill-btn");
      if (pill) {
        e.preventDefault();
        e.stopPropagation();

        const id = pill.dataset.ingredientId;
        if (id) toggleIngredient(id);
        return;
      }

      const rm = e.target.closest?.(".chip-remove");
      if (rm) {
        e.preventDefault();
        e.stopPropagation();

        const id = rm.dataset.removeId;
        if (id) {
          removeHiddenIngredient(id);
          emitFiltersChanged();
        }
      }
    });
  }

  /* =========================
     Clear selected
  ========================= */
  function bootClearSelected() {
    const btn = document.getElementById("clear-selected");
    if (!btn) return;

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      document
        .querySelectorAll(`#filters-form input[name="ingredient"]`)
        .forEach((n) => n.remove());
      emitFiltersChanged();
    });
  }

  /* =========================
     Category + strict filters
  ========================= */
  function bootCategoryFilter() {
    const sel = document.getElementById("category-select");
    const hidden = document.getElementById("category-hidden");
    if (!sel || !hidden) return;

    sel.addEventListener("change", () => {
      hidden.value = sel.value || "";
      emitFiltersChanged();
    });
  }

  function bootStrictFilter() {
    const chk = document.getElementById("strict-check");
    const hidden = document.getElementById("strict-hidden");
    if (!chk || !hidden) return;

    chk.addEventListener("change", () => {
      hidden.value = chk.checked ? "1" : "";
      emitFiltersChanged();
    });
  }

  function bootSearchSync() {
    const searchInput = document.getElementById("ingredient-search-input");
    const hiddenSearch = document.getElementById("hidden-search");

    if (!searchInput || !hiddenSearch) return;

    searchInput.addEventListener("input", (e) => {
      hiddenSearch.value = e.target.value;
    });
  }

  /* =========================
     HTMX loading (optional)
  ========================= */
  function bootHtmxLoading() {
    document.body.addEventListener("htmx:beforeRequest", () => {
      const el = document.getElementById("ing-loading");
      if (el) el.hidden = false;
    });

    document.body.addEventListener("htmx:afterRequest", () => {
      const el = document.getElementById("ing-loading");
      if (el) el.hidden = true;
    });
  }

  function bootSearchClear() {
    const input = document.getElementById("ingredient-search-input");
    const btn = document.getElementById("clear-search-btn");
    const hiddenSearch = document.getElementById("hidden-search");

    if (!input || !btn) return;

    const toggleBtn = () => {
      btn.hidden = input.value.trim() === "";
    };

    input.addEventListener("input", toggleBtn);

    toggleBtn();

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      input.value = "";
      input.focus();
      btn.hidden = true;
      if (hiddenSearch) hiddenSearch.value = "";

      htmx.trigger(input, "searchClear");
    });
  }

  /* =========================
     Init
  ========================= */
  document.addEventListener("DOMContentLoaded", function () {
    bootIngredientHandlers();
    bootClearSelected();
    bootCategoryFilter();
    bootStrictFilter();
    bootHtmxLoading();
    bootSearchSync();
    bootSearchClear();
  });
})();
