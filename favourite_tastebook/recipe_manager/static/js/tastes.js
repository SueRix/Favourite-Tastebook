(function () {
    "use strict";

    // execute when dom is loaded
    document.addEventListener('DOMContentLoaded', () => {
        const searchInput = document.getElementById('taste-search-input');
        const categorySelect = document.getElementById('taste-category-select');

        if (searchInput) {
            // use 'input' instead of 'keyup' for better handling of clear/paste
            searchInput.addEventListener('input', filterTastes);
        }
        if (categorySelect) {
            categorySelect.addEventListener('change', filterTastes);
        }
    });

    // re-apply filters after htmx updates the dom
    document.body.addEventListener('htmx:afterSwap', function (e) {
        if (e.target.id === 'unrated-tastes-container' || e.target.id === 'rated-tastes-container') {
            filterTastes();
        }
    });

    // combined filter for text and category
    function filterTastes() {
        const searchInput = document.getElementById('taste-search-input');
        const categorySelect = document.getElementById('taste-category-select');

        if (!searchInput || !categorySelect) return;

        const query = searchInput.value.toLowerCase();
        const selectedCategory = categorySelect.value.toLowerCase();

        const rows = document.querySelectorAll('#unrated-tastes-container .taste-row');
        const groups = document.querySelectorAll('#unrated-tastes-container .taste-category-group');

        // filter individual rows
        rows.forEach(row => {
            const name = row.getAttribute('data-name') || '';
            const matchesSearch = name.includes(query);
            row.style.display = matchesSearch ? 'flex' : 'none';
        });

        // filter groups based on category select and visible rows
        groups.forEach(group => {
            const groupCat = (group.getAttribute('data-category') || '').toLowerCase();
            const matchesCategory = selectedCategory === '' || groupCat === selectedCategory;

            const visibleRows = group.querySelectorAll('.taste-row[style="display: flex;"]');
            const hasVisibleRows = visibleRows.length > 0;

            group.style.display = (matchesCategory && hasVisibleRows) ? 'block' : 'none';
        });
    }
})();