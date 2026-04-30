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
            new Event("ft:filtersChanged", {bubbles: true})
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

    function hasHiddenIngredient(id, name) {
        const byId = !!document.querySelector(`#filters-form input[name="ingredient"][value="${id}"]`);
        const byName = name ? !!document.querySelector(`#filters-form input[name="ai_selected"][value="${name}"]`) : false;
        return byId || byName;
    }

    function addHiddenIngredient(id) {
        const f = formEl();
        // If it's already there (either as ID or AI name), don't add duplicate
        if (!f || hasHiddenIngredient(id, null)) return;

        const inp = document.createElement("input");
        inp.type = "hidden";
        inp.name = "ingredient";
        inp.value = String(id);
        inp.setAttribute("data-ingredient-hidden", String(id));
        f.appendChild(inp);
    }

    function removeHiddenIngredient(id, name) {
        // 1. Remove standard ID-based inputs
        if (id) {
            document.querySelectorAll(`#filters-form input[name="ingredient"][value="${id}"]`)
                .forEach((n) => n.remove());
        }

        // 2. Remove AI Name-based inputs
        if (name) {
            document.querySelectorAll(`#filters-form input[name="ai_selected"][value="${name}"]`)
                .forEach((n) => n.remove());

            // 3. Sync visual state of the simple AI pills if they exist in DOM
            const aiBtn = document.querySelector(`.ai-pill-interactive[data-value="${name}"]`);
            if (aiBtn) {
                aiBtn.classList.remove('is-selected');
                const iconSpan = aiBtn.querySelector('.pill-plus');
                if (iconSpan) {
                    iconSpan.textContent = '+';
                    iconSpan.classList.remove('ai-pill-plus-success');
                }

                // Sync dynamic counter for AI matches
                const form = document.getElementById("filters-form");
                if (form) {
                    const activeCount = form.querySelectorAll('input[name="ai_selected"]').length;
                    const countDisplay = document.getElementById('ai-dynamic-count');
                    if (countDisplay) countDisplay.textContent = activeCount;
                }
            }
        }
    }

    function toggleIngredient(id, name) {
        if (hasHiddenIngredient(id, name)) {
            removeHiddenIngredient(id, name);
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
            // Handle standard Pill Button clicks (ignore simple AI pills, they have their own handler)
            const pill = e.target.closest?.(".pill-btn");
            if (pill && !pill.classList.contains('ai-pill-interactive')) {
                e.preventDefault();
                e.stopPropagation();

                const id = pill.dataset.ingredientId;
                const name = pill.dataset.ingredientName;
                if (id) toggleIngredient(id, name);
                return;
            }

            // Handle 'X' remove clicks inside selected chips
            const rm = e.target.closest?.(".chip-remove");
            if (rm) {
                e.preventDefault();
                e.stopPropagation();

                const id = rm.dataset.removeId;
                const name = rm.dataset.removeName;
                if (id || name) {
                    removeHiddenIngredient(id, name);
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

            // Remove standard items
            document.querySelectorAll(`#filters-form input[name="ingredient"]`).forEach((n) => n.remove());

            // Remove AI items and sync their UI state
            document.querySelectorAll(`#filters-form input[name="ai_selected"]`).forEach((n) => {
                const name = n.value;
                n.remove();

                const aiBtn = document.querySelector(`.ai-pill-interactive[data-value="${name}"]`);
                if (aiBtn) {
                    aiBtn.classList.remove('is-selected');
                    const iconSpan = aiBtn.querySelector('.pill-plus');
                    if (iconSpan) {
                        iconSpan.textContent = '+';
                        iconSpan.classList.remove('ai-pill-plus-success');
                    }
                }
            });

            // Reset AI count display
            const countDisplay = document.getElementById('ai-dynamic-count');
            if (countDisplay) countDisplay.textContent = '0';

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

            const indicator = document.getElementById('search-mode-indicator');

            const aiFlag = document.getElementById('ai-mode-flag');
            const isAiModeActive = aiFlag && aiFlag.value === "1";

            if (indicator) {
                if (chk.checked) {
                    indicator.innerHTML = '🎯 Strict Match';
                } else if (isAiModeActive) {
                    indicator.innerHTML = '✦ AI Smart Search';
                } else {
                    indicator.innerHTML = '🔍 Flexible Match';
                }
            }

            emitFiltersChanged();
        });
    }

    function bootAutoShowFilter() {
        const chk = document.getElementById("auto-show-check");
        const hidden = document.getElementById("auto-show-hidden");
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
       AI Analyzer Logic
    ========================= */

    function openAiPanel(event, btnElement) {
        // check if user is logged in via data attribute
        const isAuthenticated = btnElement.getAttribute('data-authenticated') === 'true';

        if (!isAuthenticated) {
            // stop htmx and prevent panel from clearing
            event.stopImmediatePropagation();
            event.preventDefault();

            // trigger shake animation
            btnElement.classList.add('unauthorized-shake');
            btnElement.addEventListener('animationend', () => {
                btnElement.classList.remove('unauthorized-shake');
            }, {once: true});

            return;
        }

        // standard logic for authorized users
        const standardView = document.getElementById('standard-search-view');
        const aiContainer = document.getElementById('ai-panel-container');
        const url = btnElement.getAttribute('data-ai-url');

        if (standardView) standardView.style.display = 'none';
        if (aiContainer) aiContainer.style.display = 'flex';

        const wrapper = document.getElementById('main-ingredients-wrapper');
        if (wrapper) wrapper.classList.add('in-ai-mode');

        const indicator = document.getElementById('search-mode-indicator');
        if (indicator) {
            indicator.innerHTML = '✦ AI Smart Search';
        }

        // flag that we are in ai mode
        const aiFlag = document.getElementById("ai-mode-flag");
        if (aiFlag) {
            aiFlag.value = "1";
        }

        const dismissFlag = document.getElementById("dismiss-ai-modal");
        if (dismissFlag) dismissFlag.value = "";

        // load ai panel via htmx
        htmx.ajax('GET', url, {target: '#ai-panel-container', swap: 'innerHTML'});
    }

    function toggleAdvancedIngredients() {
        const simpleView = document.getElementById('ai-simple-view');
        const advancedViewTarget = document.getElementById('ai-advanced-view');
        const toggleBtn = document.getElementById('ai-toggle-ingredients-btn');

        const standardPanel = document.getElementById('main-ingredients-wrapper');
        const standardParent = document.getElementById('standard-search-view');

        // Check if currently expanded
        const isExpanded = simpleView.style.display === 'none';

        if (!isExpanded) {
            // Expand: Hide simple pills, move main panel into AI container
            simpleView.style.display = 'none';
            advancedViewTarget.style.display = 'block';
            toggleBtn.innerHTML = '− Hide ingredients';

            if (standardPanel) {
                advancedViewTarget.appendChild(standardPanel);
            }
        } else {
            // Collapse: Show simple pills, return main panel to standard view
            simpleView.style.display = 'block';
            advancedViewTarget.style.display = 'none';
            toggleBtn.innerHTML = '+ Add ingredients';

            if (standardPanel && standardParent) {
                standardParent.appendChild(standardPanel);
            }
        }
    }

    function closeAiPanel() {
        const standardView = document.getElementById('standard-search-view');
        const aiContainer = document.getElementById('ai-panel-container');
        const standardPanel = document.getElementById('main-ingredients-wrapper');

        if (standardPanel && standardView) {
            standardView.appendChild(standardPanel);
            standardPanel.classList.remove('in-ai-mode');
        }

        if (aiContainer) {
            aiContainer.innerHTML = '';
            aiContainer.style.display = 'none';
        }

        if (standardView) {
            standardView.style.display = 'flex';
        }

        const strictCheck = document.getElementById('strict-check');
        const strictHidden = document.getElementById('strict-hidden');
        if (strictCheck && strictCheck.dataset.savedState !== undefined) {
            const shouldBeChecked = strictCheck.dataset.savedState === "true";
            strictCheck.checked = shouldBeChecked;
            if (strictHidden) strictHidden.value = shouldBeChecked ? "1" : "";
            delete strictCheck.dataset.savedState;
        }

        const indicator = document.getElementById('search-mode-indicator');
        if (indicator && strictCheck) {
            indicator.innerHTML = strictCheck.checked ? '🎯 Strict Match' : '🔍 Flexible Match';
        }

        const aiFlag = document.getElementById("ai-mode-flag");
        if (aiFlag) {
            aiFlag.value = "";
        }

        const dismissFlag = document.getElementById("dismiss-ai-modal");
        if (dismissFlag) dismissFlag.value = "";

        setTimeout(() => {
            document.body.dispatchEvent(new Event("ft:filtersChanged", {bubbles: true}));
        }, 50);
    }

    function previewAiImage(input) {
        if (input.files && input.files[0]) {
            var reader = new FileReader();
            reader.onload = function (e) {
                document.getElementById('ai-dropzone-text').style.display = 'none';
                var img = document.getElementById('ai-image-preview');
                img.src = e.target.result;
                img.style.display = 'block';
            }
            reader.readAsDataURL(input.files[0]);
        }
    }

    function applyAiResults() {
        closeAiPanel();
        setTimeout(() => {
            emitFiltersChanged();
        }, 150);
    }

    function toggleAiIngredient(btnElement) {
        const ingredientValue = btnElement.getAttribute('data-value');
        const form = document.getElementById("filters-form");
        const existingInput = form.querySelector(`input[name="ai_selected"][value="${ingredientValue}"]`);
        const iconSpan = btnElement.querySelector('.pill-plus');

        if (existingInput) {
            // Remove the ingredient from active search
            existingInput.remove();
            btnElement.classList.remove('is-selected');

            if (iconSpan) {
                iconSpan.textContent = '+';
                iconSpan.classList.remove('ai-pill-plus-success');
            }
        } else {
            const input = document.createElement("input");
            input.type = "hidden";
            input.name = "ai_selected";
            input.value = ingredientValue;
            input.classList.add("ai-injected-input");
            form.appendChild(input);

            btnElement.classList.add('is-selected');

            if (iconSpan) {
                iconSpan.textContent = '✓';
                iconSpan.classList.add('ai-pill-plus-success');
            }
        }

        // Update the visual counter
        const activeCount = form.querySelectorAll('input[name="ai_selected"]').length;
        const countDisplay = document.getElementById('ai-dynamic-count');
        if (countDisplay) {
            countDisplay.textContent = activeCount;
        }

        // Trigger the global event to update recipes via HTMX or backend fetch
        document.body.dispatchEvent(new Event("ft:filtersChanged", {bubbles: true}));
    }

    async function toggleTasteAction(btn) {
    const recipeId = btn.dataset.id;
    const actionType = btn.dataset.actionType; // "like" или "dislike"
    const isActive = btn.dataset.isActive === "true";

    btn.style.pointerEvents = "none";

    try {
        if (!isActive) {
            const oppositeAction = actionType === 'like' ? 'dislike' : 'like';
            const container = btn.closest('.taste-btn-group') || btn.parentElement;
            const oppositeBtn = container.querySelector(`[data-action-type="${oppositeAction}"]`);

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
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            },
        });

        if (response.ok) {
            const newState = !isActive;
            btn.dataset.isActive = String(newState);

            if (newState) {
                btn.classList.add("active");
            } else {
                btn.classList.remove("active");
            }

            btn.classList.add("animating");
            setTimeout(() => btn.classList.remove("animating"), 300);
        } else {
            console.error(`Taste ${actionType} error:`, response.status);
        }
    } catch (err) {
        console.error("Network error:", err);
    } finally {
        btn.style.pointerEvents = "auto";
    }
}

    window.openAiPanel = openAiPanel;
    window.closeAiPanel = closeAiPanel;
    window.previewAiImage = previewAiImage;
    window.applyAiResults = applyAiResults;
    window.toggleAiIngredient = toggleAiIngredient;
    window.toggleAdvancedIngredients = toggleAdvancedIngredients;
    window.toggleTasteAction = toggleTasteAction;

    /* =========================
       Initialization
    ========================= */
    document.addEventListener("DOMContentLoaded", function () {
        bootIngredientHandlers();
        bootClearSelected();
        bootCategoryFilter();
        bootStrictFilter();
        bootAutoShowFilter();
        bootHtmxLoading();
        bootSearchSync();
        bootSearchClear();
    });
})();