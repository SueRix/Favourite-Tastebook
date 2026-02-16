/**
 * saved_recipes.js
 * Handles UI interactions for the Saved Recipes page.
 * Includes smooth accordion animations and HTMX event handling for deletions.
 */

document.addEventListener('DOMContentLoaded', () => {
    initAccordions();
    initHtmxListeners();
});

/**
 * Initializes smooth expansion/collapse for details elements.
 * Replaces the default jumpy <details> behavior.
 */
function initAccordions() {
    const details = document.querySelectorAll('details.saved-card');

    details.forEach((targetDetail) => {
        const summary = targetDetail.querySelector('summary');
        const content = targetDetail.querySelector('.saved-content');

        summary.addEventListener('click', (e) => {
            e.preventDefault(); // Prevent default instant toggle

            if (targetDetail.open) {
                // Close animation
                summary.classList.remove('active');
                slideUp(content, () => {
                    targetDetail.open = false;
                });
            } else {
                // Open animation
                targetDetail.open = true;
                summary.classList.add('active');
                slideDown(content);
            }
        });
    });
}

/**
 * HTMX Event Listeners
 * Handles the "before" and "after" states of recipe deletion.
 */
function initHtmxListeners() {
    // Before sending the delete request: add a loading state (opacity drop)
    document.body.addEventListener('htmx:configRequest', (event) => {
        if (event.target.classList.contains('btn-delete')) {
            const card = event.target.closest('.saved-card');
            if (card) {
                card.style.transition = 'all 0.3s ease';
                card.style.opacity = '0.5';
                card.style.pointerEvents = 'none'; // Prevent double clicks
            }
        }
    });

    // After the element is swapped (removed) from DOM, check if list is empty
    document.body.addEventListener('htmx:afterSwap', (event) => {
        checkEmptyState();
    });
}

/**
 * Checks if there are any recipes left.
 * If not, reveals the "Empty State" message hidden in the DOM.
 */
function checkEmptyState() {
    // Check for remaining cards
    const cards = document.querySelectorAll('.saved-card');

    // If no cards remain
    if (cards.length === 0) {
        // Check if the server-rendered empty state exists (from first load)
        const initialEmpty = document.querySelector('.empty-message-initial');

        // If server-block is missing (meaning we deleted everything dynamically), show the JS block
        if (!initialEmpty) {
            const jsEmptyState = document.getElementById('js-empty-state');
            if (jsEmptyState) {
                jsEmptyState.style.display = 'block';
                // Small fade-in animation
                jsEmptyState.style.opacity = '0';
                setTimeout(() => {
                    jsEmptyState.style.transition = 'opacity 0.5s';
                    jsEmptyState.style.opacity = '1';
                }, 10);
            }
        }
    }
}

/**
 * Utility: Slide Down Animation
 */
function slideDown(element) {
    element.style.height = '0px';
    element.style.opacity = '0';
    element.style.display = 'block';

    // Force reflow
    element.scrollHeight;

    element.style.transition = 'height 0.3s ease, opacity 0.3s ease';
    element.style.height = element.scrollHeight + 'px';
    element.style.opacity = '1';

    // Cleanup after animation
    setTimeout(() => {
        element.style.height = 'auto';
    }, 300);
}

/**
 * Utility: Slide Up Animation
 */
function slideUp(element, callback) {
    element.style.height = element.scrollHeight + 'px';
    element.style.transition = 'height 0.3s ease, opacity 0.2s ease';

    requestAnimationFrame(() => {
        element.style.height = '0px';
        element.style.opacity = '0';
    });

    setTimeout(() => {
        element.style.display = 'none';
        if (callback) callback();
    }, 300);
}