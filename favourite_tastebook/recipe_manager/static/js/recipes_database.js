/* ==========================================================================
   Recipes Database — modal interactions.
   Defines toggleFavorite / toggleTasteAction (shared with home page contracts)
   and adds modal close behavior (button, ESC, click-outside).
   ========================================================================== */
(function () {
    "use strict";

    /**
     * Reads a cookie value by name. Used to grab the CSRF token.
     */
    function getCookie(name) {
        if (!document.cookie) return null;
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === name + "=") {
                return decodeURIComponent(cookie.substring(name.length + 1));
            }
        }
        return null;
    }

    /**
     * Locates the modal slot used to host the recipe detail partial.
     */
    function modalSlot() {
        return document.getElementById("rdb-modal-slot");
    }

    /**
     * Empties the modal slot, effectively closing the recipe detail view.
     * Exposed globally because it is wired via inline onclick in the partial.
     */
    function closeRecipeDetail() {
        const slot = modalSlot();
        if (slot) slot.innerHTML = "";
    }

    /**
     * Toggles the saved/favorite state of a recipe via the existing
     * /home/saved/<recipe_id>/ endpoint. Mirrors the home page behavior.
     */
    async function toggleFavorite(btn) {
        const recipeId = btn.dataset.id;
        const isSaved = btn.dataset.isSaved === "true";
        const method = isSaved ? "DELETE" : "POST";
        const url = `/home/saved/${recipeId}/`;

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
                const newState = !isSaved;
                btn.dataset.isSaved = String(newState);
                btn.classList.toggle("active", newState);
                btn.classList.add("animating");
                setTimeout(() => btn.classList.remove("animating"), 300);
            } else {
                console.error("Save error:", response.status);
            }
        } catch (err) {
            console.error("Network error:", err);
        } finally {
            btn.style.pointerEvents = "auto";
        }
    }

    /**
     * Toggles like/dislike state on the recipe and clears the opposite
     * action if it was set. Hits /home/api/tastes/recipe/<id>/{like|dislike}/.
     */
    async function toggleTasteAction(btn) {
        const recipeId = btn.dataset.id;
        const actionType = btn.dataset.actionType;
        const isActive = btn.dataset.isActive === "true";

        btn.style.pointerEvents = "none";
        try {
            // When activating one side, clear the opposite side first.
            if (!isActive) {
                const oppositeAction = actionType === "like" ? "dislike" : "like";
                const container = btn.parentElement;
                const oppositeBtn = container && container.querySelector(`[data-action-type="${oppositeAction}"]`);

                if (oppositeBtn && oppositeBtn.dataset.isActive === "true") {
                    const oppRes = await fetch(`/home/api/tastes/recipe/${recipeId}/${oppositeAction}/`, {
                        method: "DELETE",
                        headers: {
                            "X-CSRFToken": getCookie("csrftoken"),
                            "X-Requested-With": "XMLHttpRequest",
                        },
                    });
                    if (oppRes.ok) {
                        oppositeBtn.dataset.isActive = "false";
                        oppositeBtn.classList.remove("active");
                    }
                }
            }

            const method = isActive ? "DELETE" : "POST";
            const url = `/home/api/tastes/recipe/${recipeId}/${actionType}/`;

            const response = await fetch(url, {
                method: method,
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            if (response.ok) {
                const newState = !isActive;
                btn.dataset.isActive = String(newState);
                btn.classList.toggle("active", newState);
            }
        } catch (err) {
            console.error("Network error:", err);
        } finally {
            btn.style.pointerEvents = "auto";
        }
    }

    // ESC closes the modal.
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeRecipeDetail();
    });

    // Click on the dimmed backdrop (overlay itself) closes the modal,
    // but clicking on the inner container should not.
    document.addEventListener("click", (e) => {
        const overlay = document.getElementById("rdb-modal-overlay");
        if (overlay && e.target === overlay) {
            closeRecipeDetail();
        }
    });


    /* ----------------------------------------------------------------------
       Search mode (Keyword vs. Semantic).
       The active mode lives in a hidden input that htmx pulls in via
       hx-include, so the server always receives the strategy key it expects
       ("keyword" / "vector"). Everything below only keeps that input, the tab
       styling and localStorage in sync.
       ---------------------------------------------------------------------- */

    const MODE_STORAGE_KEY = "rdb-search-mode";
    const DEFAULT_MODE = "keyword";

    const MODE_COPY = {
        keyword: {
            placeholder: "Type a keyword (e.g. pasta, chicken, soup)...",
            note: "Exact matches in titles and descriptions.",
        },
        vector: {
            placeholder: "Describe a dish (e.g. creamy tomato soup), then press Enter...",
            note: "Meaning-based search. Press Enter or the magnifier to run it.",
        },
    };

    function modeInput() {
        return document.getElementById("rdb-mode-input");
    }

    function searchInput() {
        return document.getElementById("rdb-search-input");
    }

    /**
     * True while the classic SQL engine is selected. Called from the input's
     * hx-trigger filter, so it must stay on the global scope: live keystroke
     * search is allowed in keyword mode only, and never fires an embedding call.
     */
    function rdbIsKeywordMode() {
        const hidden = modeInput();
        return !hidden || hidden.value !== "vector";
    }

    /**
     * Reads the last used mode, falling back to keyword when storage is
     * unavailable (private windows) or holds an unknown value.
     */
    function readStoredMode() {
        try {
            const stored = localStorage.getItem(MODE_STORAGE_KEY);
            return MODE_COPY[stored] ? stored : DEFAULT_MODE;
        } catch (err) {
            return DEFAULT_MODE;
        }
    }

    function storeMode(mode) {
        try {
            localStorage.setItem(MODE_STORAGE_KEY, mode);
        } catch (err) {
            // Remembering the choice is a convenience, not a requirement.
        }
    }

    /**
     * Applies a mode to the whole search bar: hidden input, tab state and copy.
     * When `rerun` is set, the search is re-issued so the visible results never
     * belong to the engine the user just switched away from.
     */
    function applyMode(mode, rerun) {
        const copy = MODE_COPY[mode] || MODE_COPY[DEFAULT_MODE];
        const input = searchInput();
        const hidden = modeInput();
        const note = document.getElementById("rdb-mode-note");

        if (hidden) hidden.value = mode;
        if (input) input.placeholder = copy.placeholder;
        if (note) note.textContent = copy.note;

        document.querySelectorAll(".rdb-mode-tab").forEach((tab) => {
            const isActive = tab.dataset.mode === mode;
            tab.classList.toggle("active", isActive);
            tab.setAttribute("aria-selected", String(isActive));
        });

        // Below the 2-char threshold the server only renders a hint, so there
        // is nothing to refresh and no reason to hit the vector backend.
        if (rerun && input && input.value.trim().length >= 2) {
            htmx.trigger(input, "rdbModeChanged");
        }
    }

    document.addEventListener("click", (e) => {
        const tab = e.target.closest && e.target.closest(".rdb-mode-tab");
        if (!tab || tab.classList.contains("active")) return;

        const mode = tab.dataset.mode;
        storeMode(mode);
        applyMode(mode, true);
    });

    // Restore the previous choice before the first request can go out.
    document.addEventListener("DOMContentLoaded", () => {
        if (modeInput()) applyMode(readStoredMode(), false);
    });

    // Expose to global scope: the inline onclick handlers in the partial rely on these names.
    window.toggleFavorite = toggleFavorite;
    window.toggleTasteAction = toggleTasteAction;
    window.closeRecipeDetail = closeRecipeDetail;
    // Needed by the hx-trigger filter on the search input.
    window.rdbIsKeywordMode = rdbIsKeywordMode;
})();
