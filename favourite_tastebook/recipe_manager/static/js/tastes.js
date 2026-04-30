(function () {
    "use strict";

    function applyTabState(target) {
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        document.querySelectorAll('.target-' + target).forEach(c => c.classList.add('active'));

        const categorySelect = document.getElementById('taste-category-select');
        if (categorySelect) {
            categorySelect.style.display = target === 'cuisines' ? 'none' : 'block';
        }
        filterTastes();
    }

    document.addEventListener('DOMContentLoaded', () => {
        const searchInput = document.getElementById('taste-search-input');
        const categorySelect = document.getElementById('taste-category-select');

        if (searchInput) searchInput.addEventListener('input', filterTastes);
        if (categorySelect) categorySelect.addEventListener('change', filterTastes);

        const tabs = document.querySelectorAll('.taste-tab');

        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                const target = tab.getAttribute('data-target');
                applyTabState(target);

                if (searchInput) {
                    searchInput.value = '';
                    filterTastes();
                }
            });
        });
    });

    document.body.addEventListener('htmx:afterSwap', function (e) {
        if (e.target.id === 'unrated-tastes-container' || e.target.id === 'rated-tastes-container') {
            const activeTab = document.querySelector('.taste-tab.active');
            if (activeTab) {
                const target = activeTab.getAttribute('data-target');
                applyTabState(target);
            }
        }
    });

    function filterTastes() {
        const searchInput = document.getElementById('taste-search-input');
        const categorySelect = document.getElementById('taste-category-select');

        if (!searchInput || !categorySelect) return;

        const query = searchInput.value.toLowerCase();
        const selectedCategory = categorySelect.value.toLowerCase();

        const rows = document.querySelectorAll('.tab-content.active .taste-row');
        const groups = document.querySelectorAll('.tab-content.active .taste-category-group');

        rows.forEach(row => {
            const name = row.getAttribute('data-name') || '';
            const matchesSearch = name.includes(query);
            row.style.display = matchesSearch ? 'flex' : 'none';
        });

        groups.forEach(group => {
            const groupCat = (group.getAttribute('data-category') || '').toLowerCase();
            const matchesCategory = selectedCategory === '' || groupCat === selectedCategory || groupCat === 'all';

            const visibleRows = group.querySelectorAll('.taste-row[style="display: flex;"]');
            const hasVisibleRows = visibleRows.length > 0;

            group.style.display = (matchesCategory && hasVisibleRows) ? 'block' : 'none';
        });
    }
})();