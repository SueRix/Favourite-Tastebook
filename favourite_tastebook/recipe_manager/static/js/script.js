"use strict";

let selectedIngredients = [];

const searchInput = document.getElementById('semanticSearchInput');
const allIngredientsList = document.querySelector('.all-ingredients-list');

// Получаем начальные данные об ингредиентах из списка доступных ингредиентов
let ingredientsElements = Array.from(document.querySelectorAll('.available-ingredient'));
let ingredientsData = ingredientsElements.map(li => ({
    name: li.dataset.name,
    id: li.dataset.id
}));

// Добавление ингредиента в список выбранных ингредиентов
function addIngredient(name) {
    if (!selectedIngredients.includes(name)) {
        selectedIngredients.push(name);
        updateSelectedIngredients();
        fetchRecipes();
    }
}

// Удаление ингредиента из списка выбранных ингредиентов
function removeIngredient(name) {
    selectedIngredients = selectedIngredients.filter(ing => ing !== name);
    updateSelectedIngredients();
    fetchRecipes();
}

// Обновление DOM для списка выбранных ингредиентов
function updateSelectedIngredients() {
    const list = document.querySelector(".selected-ingredients");
    list.innerHTML = "";
    if (selectedIngredients.length === 0) {
        list.innerHTML = `<li class="no-ingredients">❌ No ingredients selected yet.</li>`;
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

// Запрос рецептов по выбранным ингредиентам
function fetchRecipes() {
    const queryParams = selectedIngredients.join(',');
    const url = `/api/filter_recipes/?ingredients=${encodeURIComponent(queryParams)}`;
    fetch(url)
        .then(response => response.json())
        .then(data => {
            const recipesContainer = document.getElementById('recipes-result');
            recipesContainer.innerHTML = "";
            if (data.recipes && data.recipes.length > 0) {
                data.recipes.forEach(r => {
                    recipesContainer.innerHTML += `
            <li>
              <strong>${r.name}</strong> (time: ${r.cook_time || '-'} min)
              <p>${r.instructions || ''}</p>
            </li>`;
                });
            } else {
                recipesContainer.innerHTML = "<li>There are no suitable recipes.</li>";
            }
        })
        .catch(err => {
            console.error('Error fetching recipes:', err);
        });
}

// Фильтрация ингредиентов по введённому запросу
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
          <button class="btn btn-favorite favorite-ingredient-btn" data-is-favorite="false" data-ingredient-id="${ingredient.id}">⭐</button>
        </div>
      </li>
    `;
    });
}

// Универсальная функция для обновления списка избранных ингредиентов
function updateFavoriteIngredientsList() {
    fetch('/api/favorite_ingredient/', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        const favoriteIngredientsList = document.querySelector('.favorite-ingredients');
        if (!favoriteIngredientsList) {
            console.error("Error: .favorite-ingredients element not found!");
            return;
        }
        favoriteIngredientsList.innerHTML = "";
        if (data.favorite_ingredients && data.favorite_ingredients.length > 0) {
            data.favorite_ingredients.forEach(favIngredient => {
                favoriteIngredientsList.innerHTML += `
                    <li class="ingredient-item">
                        ⭐ ${favIngredient.name}
                        <button class="remove-btn" onclick="toggleFavorite('${favIngredient.id}', false)">❌</button>
                    </li>
                `;
            });
        } else {
            favoriteIngredientsList.innerHTML = `<li class="no-ingredients">❌ You have no favorite ingredients yet.</li>`;
        }
    })
    .catch(error => {
        console.error('Error fetching favorite ingredients:', error);
    });
}

// Универсальная функция для переключения состояния избранного ингредиента (добавление/удаление)
function toggleFavorite(ingredientId, add) {
    fetch('/api/favorite_ingredient/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            ingredient_id: ingredientId,
            action: add ? 'add' : 'remove'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            updateFavoriteIngredientsList();
        } else {
            console.error('Error toggling favorite:', data.message);
        }
    })
    .catch(error => {
        console.error('Fetch error in toggleFavorite:', error);
    });
}

// Обработчик поиска ингредиентов по вводу в поле
searchInput.addEventListener('input', function () {
    filterIngredients(this.value);
});

// Обработчик событий для списка всех ингредиентов: добавление и переключение избранного
allIngredientsList.addEventListener('click', function (event) {
    if (event.target.classList.contains('btn-add-small')) {
        addIngredient(event.target.dataset.name);
    }
    if (event.target.classList.contains('btn-favorite')) {
        const ingredientId = event.target.dataset.ingredientId;
        const isFavorite = event.target.dataset.isFavorite === 'true';
        toggleFavorite(ingredientId, !isFavorite);
    }
});

// Получение CSRF-токена
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

// Инициализация: фильтруем ингредиенты (показываем все) и обновляем список избранных ингредиентов при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    filterIngredients('');
    updateFavoriteIngredientsList();
});
