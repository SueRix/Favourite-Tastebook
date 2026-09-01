/* Recipe Studio.
 *
 * The conversation and the draft are one screen but two independent things: the
 * chat appends messages, the editor owns a recipe object. They meet at exactly
 * one point — a reply may carry a recipe, which is printed in the log as a card,
 * and only a click on that card decides what happens to it: it goes into the
 * editor to be reworked, or straight into the creations list as it stands.
 *
 * Everything the server sends is written with textContent, never innerHTML: the
 * replies are text a language model wrote, and a recipe title is text a person
 * typed. Neither is markup.
 */
(function () {
    "use strict";

    const root = document.querySelector(".studio");
    if (!root) return;

    const CHAT_URL = root.dataset.chatUrl;
    const RESET_URL = root.dataset.resetUrl;
    const SAVE_URL = root.dataset.saveUrl;
    const CREATIONS_URL = root.dataset.creationsUrl;
    // Reversed with a placeholder id, since the template cannot know the real one.
    const CREATION_URL = root.dataset.creationUrl;
    const SETTINGS_URL = root.dataset.settingsUrl;
    const CSRF = root.dataset.csrf;

    const els = {
        log: document.getElementById("chat-log"),
        hint: document.getElementById("chat-hint"),
        form: document.getElementById("chat-form"),
        input: document.getElementById("chat-input"),
        send: document.getElementById("chat-send"),
        reset: document.getElementById("studio-reset"),

        settings: document.getElementById("chat-settings"),
        settingsToggle: document.getElementById("studio-settings-toggle"),
        settingsStatus: document.getElementById("settings-status"),
        headChat: document.getElementById("studio-head-chat"),
        headSettings: document.getElementById("studio-head-settings"),
        sourceInput: document.getElementById("set-recipe-source"),
        sourceDatabase: document.getElementById("source-label-database"),
        sourceAi: document.getElementById("source-label-ai"),

        empty: document.getElementById("draft-empty"),
        editor: document.getElementById("draft-editor"),
        status: document.getElementById("draft-status"),
        save: document.getElementById("draft-save"),
        remove: document.getElementById("draft-delete"),
        close: document.getElementById("draft-close"),
        title: document.getElementById("draft-title"),
        cuisine: document.getElementById("draft-cuisine"),
        time: document.getElementById("draft-time"),
        ingredients: document.getElementById("ingredient-list"),
        steps: document.getElementById("step-list"),
        addIngredient: document.getElementById("add-ingredient"),
        addStep: document.getElementById("add-step"),

        creations: document.getElementById("creations"),
        creationsList: document.getElementById("creations-list"),
        creationsEmpty: document.getElementById("creations-empty"),
        creationsCount: document.getElementById("creations-count"),
        creationsToggle: document.getElementById("creations-toggle"),
        creationsClose: document.getElementById("creations-close")
    };

    function readJson(id, fallback) {
        const node = document.getElementById(id);
        if (!node) return fallback;
        try {
            return JSON.parse(node.textContent);
        } catch (e) {
            return fallback;
        }
    }

    const UNITS = readJson("units-data", ["g"]);
    const IMPORTANCE = readJson("importance-data", ["required"]);
    let creations = readJson("creations-data", []);

    // The catalogue is already on the page as the datalist; reusing it avoids
    // shipping the same 120 names twice.
    const KNOWN = new Set(
        Array.from(document.querySelectorAll("#ingredient-options option"))
            .map(function (o) { return o.value; })
    );

    let busy = false;
    let hasDraft = false;
    /* Which stored creation the editor is showing, if any — null while the pane
       holds something that exists nowhere but on this screen.
     *
     * It is the difference between the two states the pane can be in, and every
     * control in the header reads it: what the Save button does, whether there
     * is anything to delete, and whether a deletion somewhere else on the page
     * was a deletion of THIS. The title is kept beside it because the field can
     * be edited, and a confirmation dialog must name the recipe that is about to
     * go, not the new name somebody just typed over it.
     */
    let openCreationId = null;
    let openCreationTitle = "";

    function toast(text, level, actionText, actionHref) {
        if (window.FT && window.FT.toast) {
            window.FT.toast({text: text, level: level || "info", actionText: actionText, actionHref: actionHref});
        }
    }

    /* ------------------------------------------------------------ chat log */

    function scrollLog() {
        els.log.scrollTop = els.log.scrollHeight;
    }

    function addMessage(text, kind) {
        if (els.hint) els.hint.remove();
        const node = document.createElement("div");
        node.className = "msg msg--" + kind;
        node.textContent = text;
        els.log.appendChild(node);
        scrollLog();
        return node;
    }

    function addTyping() {
        if (els.hint) els.hint.remove();
        const node = document.createElement("div");
        node.className = "msg msg--agent msg--typing";
        for (let i = 0; i < 3; i++) node.appendChild(document.createElement("span"));
        node.setAttribute("aria-label", "The assistant is thinking");
        els.log.appendChild(node);
        scrollLog();
        return node;
    }

    /* --------------------------------------------------------- recipe cards */

    /* A proposal is not the draft yet.
     *
     * The reply above it is prose — it says what the dish is and why, and it
     * glosses over the parts a cook actually needs. The structured version of
     * that same dish is printed right under it, ingredients and steps in the
     * shape the editor will take them, so the person can see what the assistant
     * really built before deciding what to do with it.
     *
     * Two decisions, because there are only two: rework it, or keep it. The card
     * asks both plainly rather than making "keep it as it is" a trip through an
     * editor nobody wanted to open. Either way the card collapses to a line
     * afterwards: from that moment the recipe lives elsewhere, and a second copy
     * of it still sitting in the log would only invite editing the wrong one.
     */

    function formatAmount(value) {
        const number = Number(value);
        if (!isFinite(number)) return String(value);
        // 2.00 is a database artefact; a person reads "2".
        return String(Math.round(number * 100) / 100);
    }

    function proposalMeta(draft) {
        const bits = [];
        if (draft.cuisine) bits.push(draft.cuisine);
        bits.push((draft.cook_time_minutes || 30) + " min");
        bits.push((draft.ingredients || []).length + " ingredients");
        bits.push((draft.steps || []).length + " steps");
        return bits.join(" • ");
    }

    function proposalBlock(heading, body) {
        const wrap = document.createElement("div");
        wrap.className = "proposal-block";
        const title = document.createElement("p");
        title.className = "proposal-block-title";
        title.textContent = heading;
        wrap.append(title, body);
        return wrap;
    }

    function proposalIngredients(lines) {
        const list = document.createElement("ul");
        list.className = "proposal-ings";

        lines.forEach(function (line) {
            const item = document.createElement("li");

            const name = document.createElement("span");
            name.className = "proposal-ing-name";
            name.textContent = line.name;

            const amount = document.createElement("span");
            amount.className = "proposal-ing-amount";
            amount.textContent = formatAmount(line.amount) + " " + (line.unit || "");

            item.append(name, amount);

            // Anything the dish does not depend on says so, and says it quietly.
            if (line.importance && line.importance !== "required") {
                item.classList.add("proposal-ing--soft");
                const tag = document.createElement("span");
                tag.className = "proposal-ing-tag";
                tag.textContent = line.importance;
                item.appendChild(tag);
            }

            // A name the catalogue does not know cannot be saved, and the person
            // should learn that here rather than from a refused save.
            if (!KNOWN.has(String(line.name || "").trim().toLowerCase())) {
                item.classList.add("proposal-ing--unknown");
                item.title = "Not in the ingredient list — rename it in the draft before saving";
            }

            list.appendChild(item);
        });

        return list;
    }

    function proposalSteps(steps) {
        const list = document.createElement("ol");
        list.className = "proposal-steps";
        steps.forEach(function (step) {
            const item = document.createElement("li");
            item.textContent = step;
            list.appendChild(item);
        });
        return list;
    }

    /* The shared skeleton of every recipe printed in the log. What differs
       between a proposal and something already stored is only the kicker and the
       row of buttons, so that is all the callers below supply. */
    function recipeCard(recipe, kicker) {
        const card = document.createElement("article");
        card.className = "proposal";

        const head = document.createElement("header");
        head.className = "proposal-head";

        const kickerNode = document.createElement("p");
        kickerNode.className = "proposal-kicker";
        kickerNode.textContent = kicker;

        const title = document.createElement("h4");
        title.className = "proposal-title";
        title.textContent = recipe.title || "Untitled dish";

        const meta = document.createElement("p");
        meta.className = "proposal-meta";
        meta.textContent = proposalMeta(recipe);

        head.append(kickerNode, title, meta);

        const body = document.createElement("div");
        body.className = "proposal-body";
        if ((recipe.ingredients || []).length) {
            body.appendChild(proposalBlock("Ingredients", proposalIngredients(recipe.ingredients)));
        }
        if ((recipe.steps || []).length) {
            body.appendChild(proposalBlock("Steps", proposalSteps(recipe.steps)));
        }

        const actions = document.createElement("div");
        actions.className = "proposal-actions";

        const outcome = document.createElement("p");
        outcome.className = "proposal-moved";
        outcome.hidden = true;

        card.append(head, body, actions, outcome);
        els.log.appendChild(card);
        scrollLog();

        return {
            card: card,
            actions: actions,
            /* Collapses the card to its heading and says what became of it. */
            settle: function (text) {
                body.hidden = true;
                actions.hidden = true;
                outcome.textContent = text;
                outcome.hidden = false;
                card.classList.add("proposal--moved");
                scrollLog();
            }
        };
    }

    /* `autoload` is the server's answer, not the browser's guess: the setting
       may have been changed in another tab since this page was rendered. */
    function addProposal(draft, autoload) {
        const parts = recipeCard(draft, "Proposed recipe");

        const keep = document.createElement("button");
        keep.type = "button";
        keep.className = "btn btn-small proposal-keep";
        keep.textContent = "Save recipe";

        const manage = document.createElement("button");
        manage.type = "button";
        manage.className = "studio-ghost-btn proposal-take";
        manage.textContent = "Edit in draft";

        const note = document.createElement("p");
        note.className = "proposal-note";
        note.textContent = "Nothing is stored until you choose.";

        parts.actions.append(keep, manage, note);

        function moveToDraft(outcome) {
            renderDraft(draft, "Moved from the chat — edit anything, then save");
            parts.settle(outcome);
            toast("The recipe is in the draft pane", "success");
        }

        manage.addEventListener("click", function () {
            moveToDraft("Moved to the draft — edit it on the right.");
        });

        keep.addEventListener("click", async function () {
            keep.disabled = true;
            manage.disabled = true;
            keep.textContent = "Saving…";

            const result = await storeRecipe(draft);

            if (!result.ok) {
                // The card stays open: the recipe is still worth editing, and
                // the draft pane is where every one of these failures is fixed.
                keep.disabled = false;
                manage.disabled = false;
                keep.textContent = "Save recipe";
                toast(result.message, result.level);
                return;
            }

            parts.settle("Saved to your creations.");
            toast("Saved: " + (result.title || draft.title), "success");
        });

        /* The setting that hands the editor over without being asked.
         *
         * It is applied last, after both buttons exist, so the card the person
         * would have clicked is exactly the card that moved itself. And it is
         * refused whenever the editor holds unsaved work: the whole reason the
         * proposal normally waits in the log is that taking the pane over would
         * discard edits nobody agreed to lose, and a switch labelled as a
         * convenience must not become the one thing that does that. When it
         * declines, the card says why and stays clickable. */
        if (autoload) {
            if (draftIsDisposable()) {
                moveToDraft("Opened in the draft pane.");
            } else {
                note.textContent = "Your draft has unsaved changes, so this one stayed here.";
            }
        }

        return parts.card;
    }

    /* The agent may also save a dish itself, in the middle of a turn. Nothing is
       left to decide then — the card only reports what happened and offers the
       one thing still useful: opening it to make a variant.

       This is the card people actually see, because the assistant reaches for
       save_generated_recipe far more readily than for propose_recipe. It
       therefore has to honour the autoload switch exactly as a proposal does —
       when it did not, the switch looked broken, since the path it covered was
       the rarer of the two. */
    function addSavedNotice(recipe, autoload) {
        const parts = recipeCard(recipe, "Saved by the assistant");

        const open = document.createElement("button");
        open.type = "button";
        open.className = "studio-ghost-btn proposal-take";
        open.textContent = "Open in draft";

        const note = document.createElement("p");
        note.className = "proposal-note";
        note.textContent = "Already in your creations.";

        parts.actions.append(open, note);

        function openIt(outcome) {
            openCreation(recipe);
            parts.settle(outcome);
        }

        open.addEventListener("click", function () {
            openIt("Opened in the draft pane.");
        });

        if (autoload) {
            if (draftIsDisposable()) {
                openIt("Opened in the draft pane.");
            } else {
                note.textContent = "Your draft has unsaved changes, so this one stayed here.";
            }
        }

        return parts.card;
    }

    /* --------------------------------------------------------- draft editor */

    function makeSelect(values, current, className) {
        const select = document.createElement("select");
        select.className = "draft-input " + className;
        values.forEach(function (value) {
            const option = document.createElement("option");
            option.value = value;
            option.textContent = value;
            if (value === current) option.selected = true;
            select.appendChild(option);
        });
        return select;
    }

    function markKnown(input) {
        const known = KNOWN.has(input.value.trim().toLowerCase());
        input.closest(".ing-row").classList.toggle("ing-row--unknown", !known);
        return known;
    }

    function ingredientRow(line) {
        const row = document.createElement("div");
        row.className = "ing-row";

        const name = document.createElement("input");
        name.type = "text";
        name.className = "draft-input ing-name";
        name.setAttribute("list", "ingredient-options");
        name.value = line.name || "";
        name.placeholder = "ingredient";

        const amount = document.createElement("input");
        amount.type = "number";
        amount.className = "draft-input ing-amount";
        amount.min = "0.01";
        amount.max = "9999.99";
        amount.step = "0.01";
        amount.value = line.amount != null ? line.amount : 1;

        const unit = makeSelect(UNITS, line.unit || "g", "ing-unit");
        const importance = makeSelect(IMPORTANCE, line.importance || "required", "ing-importance");

        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "row-remove";
        remove.textContent = "×";
        remove.setAttribute("aria-label", "Remove ingredient");
        remove.addEventListener("click", function () {
            row.remove();
            touched();
        });

        row.append(name, amount, unit, importance, remove);

        name.addEventListener("input", function () {
            markKnown(name);
            touched();
        });
        [amount, unit, importance].forEach(function (field) {
            field.addEventListener("input", touched);
        });

        if (name.value) markKnown(name);
        return row;
    }

    function stepRow(text) {
        const row = document.createElement("li");
        row.className = "step-row";

        const area = document.createElement("textarea");
        area.className = "draft-input step-text";
        area.rows = 2;
        area.maxLength = 600;
        area.value = text || "";
        area.addEventListener("input", touched);

        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "row-remove";
        remove.textContent = "×";
        remove.setAttribute("aria-label", "Remove step");
        remove.addEventListener("click", function () {
            row.remove();
            touched();
        });

        row.append(area, remove);
        return row;
    }

    /* Save and Delete take each other's place in the header.
     *
     * A recipe that is already stored has nothing left to save — that is what
     * the greyed-out button used to say, and a dead control is a poor answer to
     * "what do I do with this now". The thing still worth doing to it is getting
     * rid of it, so that is the button that stands there instead. The moment an
     * edit makes it a different recipe again, Save comes back.
     *
     * They are never both on screen: the destructive one must not sit a slip
     * away from the one that gets pressed all day.
     */
    function syncDraftActions() {
        const stored = openCreationId !== null && els.save.disabled;
        els.remove.hidden = !stored;
        els.save.hidden = stored;
        // Close is about the pane, not about the recipe: it is there whenever
        // there is something to close, in both of the states above.
        els.close.hidden = !hasDraft;
    }

    /* Whether a new recipe may take the editor without a click.
     *
     * Two states are safe: an empty pane, and one showing a stored creation with
     * nothing edited since — that one exists in the database and is one click
     * away in the creations drawer. Anything else is work only this screen has.
     */
    function draftIsDisposable() {
        if (!hasDraft) return true;
        return openCreationId !== null && els.save.disabled;
    }

    function renderDraft(draft, statusText) {
        hasDraft = true;
        openCreationId = draft.id != null ? draft.id : null;
        openCreationTitle = openCreationId !== null ? (draft.title || "") : "";
        els.empty.hidden = true;
        els.editor.hidden = false;

        els.title.value = draft.title || "";
        els.cuisine.value = draft.cuisine || "";
        els.time.value = draft.cook_time_minutes || 30;

        els.ingredients.replaceChildren();
        (draft.ingredients || []).forEach(function (line) {
            els.ingredients.appendChild(ingredientRow(line));
        });

        els.steps.replaceChildren();
        (draft.steps || []).forEach(function (step) {
            els.steps.appendChild(stepRow(step));
        });

        setStatus(statusText || "Proposed just now — edit anything, then save");
        els.save.disabled = false;
        els.save.textContent = "Save";
        syncDraftActions();
    }

    /* Empties the editor and puts the pane back to its opening state.
     *
     * Only one thing calls it: deleting the recipe the editor is showing. The
     * rows on screen are the recipe that was just deleted, and leaving them
     * there would make the drawer's Close button hand it back looking stored —
     * a recipe the person could go on editing and would expect to still exist.
     */
    function clearDraft(statusText) {
        hasDraft = false;
        openCreationId = null;
        openCreationTitle = "";

        els.title.value = "";
        els.cuisine.value = "";
        els.time.value = "";
        els.ingredients.replaceChildren();
        els.steps.replaceChildren();

        els.editor.hidden = true;
        els.empty.hidden = false;

        setStatus(statusText || "Nothing yet");
        els.save.disabled = true;
        els.save.textContent = "Save";
        // It was disabled by the click that got us here; the next recipe needs
        // it working again.
        els.remove.disabled = false;
        syncDraftActions();
    }

    /* Opening something already stored: the same editor, but Save gives way to
       Delete, because pressing Save on an unchanged copy would only earn a
       conflict on the title that is already taken. */
    function openCreation(recipe) {
        renderDraft(recipe, "Opened from your creations");
        els.save.disabled = true;
        els.save.textContent = "Saved";
        syncDraftActions();
        els.creations.hidden = true;
    }

    function setStatus(text, saved) {
        els.status.textContent = "";
        const span = document.createElement("span");
        if (saved) span.className = "studio-saved-badge";
        span.textContent = text;
        els.status.appendChild(span);
    }

    // Any edit after a save makes it a different recipe again.
    function touched() {
        if (!hasDraft) return;
        els.save.disabled = false;
        els.save.textContent = "Save";
        syncDraftActions();
    }

    [els.title, els.cuisine, els.time].forEach(function (field) {
        field.addEventListener("input", touched);
    });

    els.addIngredient.addEventListener("click", function () {
        const row = ingredientRow({amount: 1, unit: UNITS[0], importance: "required"});
        els.ingredients.appendChild(row);
        row.querySelector(".ing-name").focus();
        touched();
    });

    els.addStep.addEventListener("click", function () {
        const row = stepRow("");
        els.steps.appendChild(row);
        row.querySelector(".step-text").focus();
        touched();
    });

    function collectDraft() {
        const ingredients = Array.from(els.ingredients.querySelectorAll(".ing-row"))
            .map(function (row) {
                return {
                    name: row.querySelector(".ing-name").value.trim().toLowerCase(),
                    amount: row.querySelector(".ing-amount").value || 1,
                    unit: row.querySelector(".ing-unit").value,
                    importance: row.querySelector(".ing-importance").value
                };
            })
            .filter(function (line) { return line.name; });

        const steps = Array.from(els.steps.querySelectorAll(".step-text"))
            .map(function (area) { return area.value.trim(); })
            .filter(Boolean);

        return {
            title: els.title.value.trim(),
            cuisine: els.cuisine.value.trim(),
            cook_time_minutes: els.time.value || 30,
            steps: steps,
            ingredients: ingredients
        };
    }

    /* -------------------------------------------------------------- saving */

    /* One save path for both buttons.
     *
     * The card and the editor send the same shape to the same endpoint, so they
     * must also fail the same way: a recipe refused from the card would be
     * refused from the editor for exactly the same reason, and a person who saw
     * two different sentences for it would reasonably think they were two
     * different problems.
     */

    function draftProblem(draft) {
        if (!draft.title) return "Give the recipe a title first";
        if (!(draft.ingredients || []).length || !(draft.steps || []).length) {
            return "A recipe needs at least one ingredient and one step";
        }

        const unknown = (draft.ingredients || [])
            .filter(function (line) { return !KNOWN.has(String(line.name || "").trim().toLowerCase()); })
            .map(function (line) { return line.name; });
        // The server would refuse this too; saying it here saves the round trip.
        if (unknown.length) return "Not in the ingredient list: " + unknown.join(", ");

        return null;
    }

    /* Returns {ok: true, title, recipeId} or {ok: false, message, level}. */
    async function storeRecipe(draft) {
        const problem = draftProblem(draft);
        if (problem) return {ok: false, message: problem, level: "warning"};

        let response;
        let data = {};
        try {
            response = await fetch(SAVE_URL, {
                method: "POST",
                headers: {"X-CSRFToken": CSRF, "Content-Type": "application/json"},
                body: JSON.stringify(draft)
            });
            data = await response.json().catch(function () { return {}; });
        } catch (e) {
            return {ok: false, message: "Could not reach the server", level: "error"};
        }

        if (!response.ok) {
            let text = data.detail || "Could not save the recipe.";
            if (data.error === "unknown_ingredients" && data.unknown) {
                text = "Not in the ingredient list: " + data.unknown.join(", ");
            } else if (data.error === "taboo_ingredient" && data.ingredients) {
                text = "You marked these as never use: " + data.ingredients.join(", ");
            } else if (data.error === "already_saved") {
                // A title is unique per user, so this is what an edited creation
                // runs into. Naming the way out beats restating the rule.
                text = "You already have a recipe with this title — rename it to keep both";
            }
            return {
                ok: false,
                message: text,
                level: response.status === 409 ? "warning" : "error"
            };
        }

        // The list on screen is not patched by hand: the server has just become
        // the only party that knows the whole truth, so it is asked for it.
        await refreshCreations();

        return {ok: true, title: data.title, recipeId: data.recipe_id};
    }

    /* ----------------------------------------------------------- creations */

    function creationUrl(id) {
        return CREATION_URL.replace(/0\/$/, String(id) + "/");
    }

    function creationRow(recipe) {
        const item = document.createElement("li");
        item.className = "creation-row";

        const open = document.createElement("button");
        open.type = "button";
        open.className = "creation-item";

        const title = document.createElement("span");
        title.textContent = recipe.title;

        const meta = document.createElement("span");
        meta.className = "creation-meta";
        const bits = [];
        if (recipe.cuisine) bits.push(recipe.cuisine);
        bits.push(recipe.cook_time_minutes + " min");
        bits.push((recipe.ingredients || []).length + " ingredients");
        meta.textContent = bits.join(" • ");

        open.append(title, meta);
        open.addEventListener("click", function () {
            openCreation(recipe);
        });

        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "creation-delete";
        remove.textContent = "×";
        remove.title = "Delete this recipe";
        remove.setAttribute("aria-label", "Delete " + recipe.title);
        remove.addEventListener("click", function () {
            deleteCreation(recipe, remove);
        });

        item.append(open, remove);
        return item;
    }

    function renderCreations() {
        els.creationsList.replaceChildren();
        creations.forEach(function (recipe) {
            els.creationsList.appendChild(creationRow(recipe));
        });

        els.creationsEmpty.hidden = creations.length > 0;
        els.creationsCount.textContent = creations.length;
    }

    /* Re-reads the list instead of editing the local copy.
     *
     * The page is not the only writer: the agent saves recipes from inside a
     * chat turn, on a request this script never sees. Refetching after every
     * write is one small query and leaves nothing to drift. A failure here is
     * deliberately quiet — the write itself succeeded, and an alarming toast
     * about a list refresh would misreport what happened.
     */
    async function refreshCreations() {
        try {
            const response = await fetch(CREATIONS_URL, {headers: {"X-Requested-With": "fetch"}});
            if (!response.ok) return false;
            const data = await response.json();
            if (!Array.isArray(data.recipes)) return false;
            creations = data.recipes;
        } catch (e) {
            return false;
        }
        renderCreations();
        return true;
    }

    /* The one delete path, whichever button asked for it — the × in the list or
       Delete in the draft header. Both name the same recipe and both have to
       leave the page in the same state afterwards. */
    async function deleteCreation(recipe, button) {
        if (!window.confirm("Delete “" + recipe.title + "”? This cannot be undone.")) return;

        button.disabled = true;

        let response;
        try {
            response = await fetch(creationUrl(recipe.id), {
                method: "DELETE",
                headers: {"X-CSRFToken": CSRF}
            });
        } catch (e) {
            button.disabled = false;
            toast("Could not reach the server", "error");
            return;
        }

        // 404 means it is already gone — the end state is the one that was asked
        // for, so the list is refreshed rather than an error shown.
        if (!response.ok && response.status !== 404) {
            button.disabled = false;
            toast("Could not delete the recipe", "error");
            return;
        }

        await refreshCreations();

        // The editor may be showing the recipe that just stopped existing, and
        // the drawer covers it: closing the drawer would then hand back a recipe
        // the person has just deleted, still looking stored. It goes with it.
        // Compared loosely because one id came from the page and one from a
        // fetch, and a string "12" must not survive as a different recipe.
        if (openCreationId !== null && Number(openCreationId) === Number(recipe.id)) {
            clearDraft("Deleted — the draft pane is empty again");
        }

        toast("Deleted: " + recipe.title, "info");
    }

    els.creationsToggle.addEventListener("click", function () {
        els.creations.hidden = !els.creations.hidden;
        // Opening the drawer is the moment a stale list would be noticed.
        if (!els.creations.hidden) refreshCreations();
    });
    els.creationsClose.addEventListener("click", function () {
        els.creations.hidden = true;
    });

    /* ------------------------------------------------------------ requests */

    function describeFailure(status, data) {
        if (status === 401) return "Your session ended. Sign in again to keep cooking.";
        if (status === 429) {
            const wait = data && data.retry_after ? Math.ceil(data.retry_after) : null;
            return wait
                ? "Too many messages — try again in " + wait + " seconds."
                : "Too many messages. Give the assistant a moment.";
        }
        return (data && data.detail) || "The assistant is unavailable right now.";
    }

    async function sendMessage(text) {
        if (busy || !text) return;
        busy = true;
        els.send.disabled = true;

        addMessage(text, "user");
        const typing = addTyping();

        let response;
        let data = {};
        try {
            response = await fetch(CHAT_URL, {
                method: "POST",
                headers: {
                    "X-CSRFToken": CSRF,
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                body: new URLSearchParams({message: text}).toString()
            });
            data = await response.json().catch(function () { return {}; });
        } catch (e) {
            typing.remove();
            addMessage("Could not reach the server. Check your connection and try again.", "error");
            busy = false;
            els.send.disabled = false;
            return;
        }

        typing.remove();

        if (!response.ok) {
            addMessage(describeFailure(response.status, data), "error");
            if (response.status === 401) {
                toast("Sign in to keep using the studio", "warning", "Sign in", document.body.dataset.loginUrl);
            }
        } else {
            addMessage(data.reply, "agent");
            // The recipe is shown in the log rather than pushed into the editor:
            // taking over the right-hand pane unasked would discard whatever the
            // person had already edited there.
            if (data.draft) addProposal(data.draft, data.autoload_draft);
            if (data.saved) {
                addSavedNotice(data.saved, data.autoload_draft);
                refreshCreations();
                toast("Saved: " + data.saved.title, "success");
            }
        }

        busy = false;
        els.send.disabled = false;
        els.input.focus();
    }

    els.form.addEventListener("submit", function (event) {
        event.preventDefault();
        const text = els.input.value.trim();
        if (!text) return;
        els.input.value = "";
        els.input.style.height = "auto";
        sendMessage(text);
    });

    // Enter sends, Shift+Enter breaks the line — the convention every chat uses.
    els.input.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            els.form.requestSubmit();
        }
    });

    els.input.addEventListener("input", function () {
        els.input.style.height = "auto";
        els.input.style.height = Math.min(els.input.scrollHeight, 140) + "px";
    });

    document.querySelectorAll(".chat-suggestion").forEach(function (button) {
        button.addEventListener("click", function () {
            sendMessage(button.textContent.trim());
        });
    });

    els.reset.addEventListener("click", async function () {
        try {
            await fetch(RESET_URL, {method: "POST", headers: {"X-CSRFToken": CSRF}});
        } catch (e) {
            toast("Could not start a new conversation", "error");
            return;
        }
        els.log.replaceChildren();
        addMessage("New conversation started. The assistant has forgotten the previous one.", "agent");
        toast("New conversation started", "info");
    });

    /* ------------------------------------------------------------ settings */

    /* The gear swaps the pane's contents rather than opening something over
       them. The conversation is not paused while you are in here — it is simply
       not on screen — so nothing about it is torn down: coming back finds the
       same log, scrolled where it was, and whatever was half-typed still in the
       box. */
    function setSettingsOpen(open) {
        els.settings.hidden = !open;
        els.log.hidden = open;
        els.form.hidden = open;
        // "New chat" belongs to the conversation, not to this panel.
        els.reset.hidden = open;
        els.headChat.hidden = open;
        els.headSettings.hidden = !open;

        const gear = els.settingsToggle.querySelector(".icon-gear");
        const chat = els.settingsToggle.querySelector(".icon-chat");
        if (gear) gear.hidden = open;
        if (chat) chat.hidden = !open;

        const label = open ? "Back to the conversation" : "Assistant settings";
        els.settingsToggle.setAttribute("aria-expanded", open ? "true" : "false");
        els.settingsToggle.setAttribute("aria-label", label);
        els.settingsToggle.title = label;

        if (open) {
            settingsNote("");
        } else {
            els.input.focus();
            scrollLog();
        }
    }

    let noteTimer = null;

    function settingsNote(text, isError) {
        window.clearTimeout(noteTimer);
        els.settingsStatus.textContent = text;
        els.settingsStatus.classList.toggle("settings-status--error", Boolean(isError));
        // A confirmation that stays becomes furniture; a failure has to be read.
        if (text && !isError) {
            noteTimer = window.setTimeout(function () {
                els.settingsStatus.textContent = "";
            }, 2200);
        }
    }

    /* Only one of the two ends of the source switch is true, so only one is lit.
       Both are also clickable, because a label naming a state is a thing people
       press to get that state. */
    function syncSourceLabels() {
        const ai = els.sourceInput.checked;
        els.sourceDatabase.classList.toggle("switch-end--active", !ai);
        els.sourceAi.classList.toggle("switch-end--active", ai);
    }

    function settingValue(input) {
        // The only non-boolean of the three: it is stored as a word so a third
        // source can be added later without turning the column inside out.
        if (input.dataset.setting === "recipe_source") {
            return input.checked ? "ai" : "database";
        }
        return input.checked;
    }

    /* One switch, one request, carrying only the field that moved.
     *
     * The click is applied optimistically and taken back if the write fails.
     * That order is the honest one: the switch shows what is stored, so it must
     * not keep showing a value the server never accepted. */
    async function persistSetting(input) {
        const field = input.dataset.setting;
        const body = {};
        body[field] = settingValue(input);

        input.disabled = true;
        settingsNote("Saving…");

        let response;
        let data = {};
        try {
            response = await fetch(SETTINGS_URL, {
                method: "POST",
                headers: {"X-CSRFToken": CSRF, "Content-Type": "application/json"},
                body: JSON.stringify(body)
            });
            data = await response.json().catch(function () { return {}; });
        } catch (e) {
            input.checked = !input.checked;
            syncSourceLabels();
            input.disabled = false;
            settingsNote("Could not reach the server — the setting was not changed.", true);
            return;
        }

        input.disabled = false;

        if (!response.ok) {
            input.checked = !input.checked;
            syncSourceLabels();
            settingsNote(data.detail || "The setting was not changed.", true);
            return;
        }

        // Rendered from the answer rather than from the click: if the server
        // stored something else, that is what the switch has to show.
        if (data.settings) {
            const stored = data.settings[field];
            input.checked = field === "recipe_source" ? stored === "ai" : Boolean(stored);
            syncSourceLabels();
        }

        settingsNote("Saved");
    }

    els.settingsToggle.addEventListener("click", function () {
        setSettingsOpen(els.settings.hidden);
    });

    // Escape is the way out of anything that covers what you were doing.
    els.settings.addEventListener("keydown", function (event) {
        if (event.key === "Escape") setSettingsOpen(false);
    });

    els.settings.querySelectorAll("input[data-setting]").forEach(function (input) {
        input.addEventListener("change", function () {
            if (input.dataset.setting === "recipe_source") syncSourceLabels();
            persistSetting(input);
        });
    });

    [[els.sourceDatabase, false], [els.sourceAi, true]].forEach(function (pair) {
        pair[0].addEventListener("click", function () {
            if (els.sourceInput.checked === pair[1] || els.sourceInput.disabled) return;
            els.sourceInput.checked = pair[1];
            syncSourceLabels();
            persistSetting(els.sourceInput);
        });
    });

    syncSourceLabels();

    /* ------------------------------------------------------------- draft save */

    els.save.addEventListener("click", async function () {
        const draft = collectDraft();

        const problem = draftProblem(draft);
        if (problem) {
            toast(problem, "warning");
            if (!draft.title) els.title.focus();
            return;
        }

        els.save.disabled = true;
        els.save.textContent = "Saving…";

        const result = await storeRecipe(draft);

        if (!result.ok) {
            els.save.disabled = false;
            els.save.textContent = "Save";
            toast(result.message, result.level);
            return;
        }

        // It is a stored creation from here on, so the header swaps Save for the
        // way back out of it.
        openCreationId = result.recipeId != null ? result.recipeId : null;
        openCreationTitle = result.title || draft.title;
        els.save.textContent = "Saved";
        setStatus("Saved to your creations", true);
        syncDraftActions();
        toast("Saved: " + result.title, "success");
    });

    /* Close empties the pane and destroys nothing.
     *
     * What it costs depends on what is in there. A stored creation costs
     * nothing at all — it is in the database and one click away in the drawer —
     * so it closes without a word. Unsaved edits exist only on this screen, and
     * closing is the one action that would lose them, so that case asks first.
     * The question names the recipe, because by then the title may have been
     * typed over several times. */
    els.close.addEventListener("click", function () {
        const unsaved = !els.save.disabled;
        if (unsaved) {
            const name = els.title.value.trim() || "this draft";
            if (!window.confirm("Close “" + name + "” without saving? The changes are lost.")) return;
        }
        clearDraft("Nothing yet");
    });

    els.remove.addEventListener("click", function () {
        if (openCreationId === null) return;
        deleteCreation(
            {id: openCreationId, title: openCreationTitle || "this recipe"},
            els.remove
        );
    });

    renderCreations();
})();
