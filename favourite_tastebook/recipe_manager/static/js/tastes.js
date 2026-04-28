// execute when dom is loaded
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('taste-search-input');
    const categorySelect = document.getElementById('taste-category-select');

    if (searchInput && categorySelect) {
        // attach event listeners
        searchInput.addEventListener('keyup', filterTastes);
        categorySelect.addEventListener('change', filterTastes);
    }
});

// combined filter for text and category
function filterTastes() {
    const query = document.getElementById('taste-search-input').value.toLowerCase();
    const selectedCategory = document.getElementById('taste-category-select').value.toLowerCase();

    const rows = document.querySelectorAll('#unrated-tastes-container .taste-row');
    const groups = document.querySelectorAll('#unrated-tastes-container .taste-category-group');

    // filter individual rows
    rows.forEach(row => {
        const name = row.getAttribute('data-name');
        const matchesSearch = name.includes(query);
        row.style.display = matchesSearch ? 'flex' : 'none';
    });

    // filter groups based on category select and visible rows
    groups.forEach(group => {
        const groupCat = group.getAttribute('data-category');
        const matchesCategory = selectedCategory === '' || groupCat === selectedCategory;

        const visibleRows = group.querySelectorAll('.taste-row[style="display: flex;"]');
        const hasVisibleRows = visibleRows.length > 0;

        group.style.display = (matchesCategory && hasVisibleRows) ? 'block' : 'none';
    });
}