let selectedIngredients = [];
const searchInput = document.getElementById('semanticSearchInput');
const allIngredientsList = document.querySelector('.all-ingredients-list');
const ingredientsElements = [...document.querySelectorAll('.available-ingredient')];
const ingredientsData = ingredientsElements.map(li => ({
    name: li.dataset.name,
    id: li.dataset.id
}));

function addIngredient(name) {
    if (!selectedIngredients.includes(name)) {
        selectedIngredients.push(name);
        updateSelectedIngredients();
        fetchRecipes();
    }
}

function removeIngredient(name) {
    selectedIngredients = selectedIngredients.filter(ing => ing !== name);
    updateSelectedIngredients();
    fetchRecipes();
}

function updateSelectedIngredients() {
    const list = document.querySelector(".selected-ingredients");
    list.innerHTML = "";

    if (selectedIngredients.length === 0) {
        list.innerHTML = `<li class="no-ingredients">
      ❌ No ingredients selected yet.
    </li>`;
        return;
    }

    selectedIngredients.forEach(ing => {
        list.innerHTML += `
      <li class="ingredient-item">
        ✅ ${ing}
        <button class="remove-btn" onclick="removeIngredient('${ing}')">✖</button>
      </li>`;
    });
}

function fetchRecipes() {
    const queryParams = selectedIngredients.join(',');
    const url = `/api/filter_recipes/?ingredients=${encodeURIComponent(queryParams)}`;

    fetch(url, {
        method: 'GET',
    })
        .then(response => response.json())
        .then(data => {
            const recipesContainer = document.getElementById('recipes-result');
            recipesContainer.innerHTML = "";

            if (data.recipes && data.recipes.length > 0) {
                data.recipes.forEach(r => {
                    recipesContainer.innerHTML += `
            <li>
              <strong>${r.name}</strong> 
              (time: ${r.cook_time || '-'} min)
              <p>${r.instructions || ''}</p>
            </li>`;
                });
            } else {
                recipesContainer.innerHTML = "<li>There are no suitable recipes.</li>";
            }
        })
        .catch(err => {
            console.error('Error:', err);
        });
}

function filterIngredients(searchTerm) {
    allIngredientsList.innerHTML = '';
    const filteredIngredients = ingredientsData.filter(ing =>
        ing.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
    filteredIngredients.forEach(ingredient => {
        allIngredientsList.innerHTML += `
      <li class="available-ingredient" data-name="${ingredient.name}" data-id="${ingredient.id}">
        ${ingredient.name}
        <div class="ingredient-buttons">
          <button class="btn btn-add-small add-ingredient-btn" data-name="${ingredient.name}">➕</button>
          <button class="btn btn-favorite favorite-ingredient-btn" data-is-favorite="false" data-ingredient-id="${ingredient.id}">⭐</button
        </div>
      </li>
    `;
    });
}

searchInput.addEventListener('input', function () {
    filterIngredients(this.value);
});

allIngredientsList.addEventListener('click', function (event) {
    if (event.target.classList.contains('btn-add-small')) {
        addIngredient(event.target.dataset.name);
    }
    if (event.target.classList.contains('btn-favorite')) {
        const ingredientId = event.target.dataset.ingredientId;
        const isFavorite = event.target.dataset.isFavorite === 'true';

        fetch('/api/favorite_ingredient/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                ingredient_id: ingredientId,
                action: isFavorite ? 'remove' : 'add'
            })
        })
            .then(response => response.json())
            .then(data => {
                console.log('Success:', data);
                event.target.dataset.isFavorite = !isFavorite;

            })
            .catch(error => {
                console.error('Error:', error);
            });
    }
});

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            let cookie = cookies[i].trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

filterIngredients('');