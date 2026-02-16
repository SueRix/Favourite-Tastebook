(function () {
  "use strict";

  /* =========================
     Helpers & Utilities
  ========================= */

  /**
   * Dispatches a custom event when filters change.
   * Other components can listen to "ft:filtersChanged".
   */
  function emitFiltersChanged() {
    document.body.dispatchEvent(
      new Event("ft:filtersChanged", { bubbles: true })
    );
  }

  /**
   * Returns the main filters form element.
   */
  function formEl() {
    return document.getElementById("filters-form");
  }

  /**
   * Retrieves a cookie value by name (Standard Django approach).
   * Used primarily for CSRF tokens.
   */
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + "=") {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  /* =========================
     Hidden Ingredients Logic
     (Manages hidden inputs for form submission)
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
      .querySelectorAll(`#filters-form input[name="ingredient"][value="${id}"]`)
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
     Favorites Logic (IVI / Cinema Style)
  ========================= */

  /**
   * Toggles the favorite status of a recipe.
   * Handles visual state changes and backend sync via fetch.
   * @param {HTMLElement} btn - The button element clicked.
   */
  async function toggleFavorite(btn) {
    const recipeId = btn.dataset.id;
    // Check current state from data attribute (string "true" or "false")
    const isSaved = btn.dataset.isSaved === "true";

    // Determine method: DELETE if saved, POST if not
    const method = isSaved ? "DELETE" : "POST";
    const url = `/home/saved/${recipeId}/`;

    // Disable pointer events to prevent double-clicking
    btn.style.pointerEvents = "none";

    try {
      const response = await fetch(url, {
        method: method,
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
        },
      });

      if (response.ok) {
        // SUCCESS: Invert the state
        const newState = !isSaved;

        // 1. Update data attribute
        btn.dataset.isSaved = String(newState);

        // 2. Toggle visual class
        if (newState) {
          btn.classList.add("active");
        } else {
          btn.classList.remove("active");
        }

        // 3. Add pop animation
        btn.classList.add("animating");
        setTimeout(() => btn.classList.remove("animating"), 300);
      } else {
        console.error("Save error:", response.status);
        // Optional: show a toast or alert here
      }
    } catch (err) {
      console.error("Network error:", err);
    } finally {
      // Re-enable button
      btn.style.pointerEvents = "auto";
    }
  }

  // EXPOSE TO GLOBAL SCOPE
  // Essential because the HTML uses onclick="toggleFavorite(this)"
  window.toggleFavorite = toggleFavorite;

  /* =========================
     Event Handlers & Bootstrapping
  ========================= */

  function bootIngredientHandlers() {
    document.addEventListener("click", (e) => {
      // Handle Pill Button clicks
      const pill = e.target.closest?.(".pill-btn");
      if (pill) {
        e.preventDefault();
        e.stopPropagation();

        const id = pill.dataset.ingredientId;
        if (id) toggleIngredient(id);
        return;
      }

      // Handle 'X' remove clicks inside chips
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

    // Initial check
    toggleBtn();

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      input.value = "";
      input.focus();
      btn.hidden = true;
      if (hiddenSearch) hiddenSearch.value = "";

      // Trigger HTMX if attached to input
      if (typeof htmx !== "undefined") {
        htmx.trigger(input, "searchClear");
      }
    });
  }

  /* =========================
     Initialization
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