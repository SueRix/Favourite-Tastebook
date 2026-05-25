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

    // Expose to global scope: the inline onclick handlers in the partial rely on these names.
    window.toggleFavorite = toggleFavorite;
    window.toggleTasteAction = toggleTasteAction;
    window.closeRecipeDetail = closeRecipeDetail;
})();
