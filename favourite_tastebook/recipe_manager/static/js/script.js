"use strict";

let selectedIngredients = [];
let mode = "list", selectedCategory = null;
const searchInput = document.getElementById("semanticSearchInput");
const allIngredientsList = document.querySelector(".all-ingredients-list");
const toggleViewBtn = document.getElementById("toggleView");

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
  list.innerHTML = selectedIngredients.length ?
    selectedIngredients.map(ing => `<li class="ingredient-item">✅ ${ing}<button class="remove-btn" onclick="removeIngredient('${ing}')">✖</button></li>`).join('') :
    `<li class="no-ingredients">❌ No ingredients selected yet.</li>`;
}

function fetchRecipes() {
  const queryParams = selectedIngredients.join(",");
  fetch(`/api/filter_recipes/?ingredients=${encodeURIComponent(queryParams)}`)
    .then(res => res.json())
    .then(data => {
      const recipesContainer = document.getElementById("recipes-result");
      recipesContainer.innerHTML = data.recipes?.length ?
        data.recipes.map(r => `<li><strong>${r.name}</strong> (time: ${r.cook_time || "-"} min)<p>${r.instructions || ""}</p></li>`).join('') :
        "<li>There are no suitable recipes.</li>";
    })
    .catch(console.error);
}

function updateFavoriteIngredientsList() {
  fetch("/api/favorite_ingredient/", {
    method: "GET", headers: {"Content-Type": "application/json", "X-CSRFToken": getCookie("csrftoken")}
  })
    .then(res => res.json())
    .then(data => {
      const favoriteIngredientsList = document.querySelector(".favorite-ingredients");
      favoriteIngredientsList.innerHTML = data.favorite_ingredients?.length ?
        data.favorite_ingredients.map(fav => `<li class="ingredient-item">⭐ ${fav.name}<button class="remove-btn" onclick="toggleFavorite('${fav.id}', false)">❌</button></li>`).join('') :
        "<li class='no-ingredients'>❌ You have no favorite ingredients yet.</li>";
    })
    .catch(console.error);
}

function toggleFavorite(ingredientId, add) {
  fetch("/api/favorite_ingredient/", {
    method: "POST",
    headers: {"Content-Type": "application/json", "X-CSRFToken": getCookie("csrftoken")},
    body: JSON.stringify({ingredient_id: ingredientId, action: add ? "add" : "remove"})
  })
    .then(res => res.json())
    .then(data => data.status === "success" ? updateFavoriteIngredientsList() : console.error("Error toggling favorite:", data.message))
    .catch(console.error);
}

function render() {
  const searchTerm = searchInput.value.trim().toLowerCase();
  const url = new URL('/api/search_ingredients/', window.location.origin);
  url.searchParams.set('q', searchTerm);
  url.searchParams.set('mode', mode);
  if (mode === "categories" && selectedCategory) url.searchParams.set('category', selectedCategory);

  fetch(url)
    .then(res => res.json())
    .then(data => {
      allIngredientsList.innerHTML = mode === "categories" ?
        selectedCategory === null ?
          data.categories?.length ? data.categories.map(cat => `<li class="available-category"><button class="btn category-btn" data-cat-name="${cat}">${cat}</button></li>`).join('') : "<li class='no-ingredients'>No categories found.</li>" :
          `<li class="ingredient-item"><button class="btn" onclick="goBackToCategories()">Back to categories</button></li>` + (data.ingredients?.length ? data.ingredients.map(item => renderIngredientItem(item)).join('') : "<li class='no-ingredients'>No ingredients in this category.</li>") :
        data.ingredients?.length ? data.ingredients.map(item => renderIngredientItem(item)).join('') : "<li class='no-ingredients'>No ingredients found.</li>";
    })
    .catch(console.error);
}

function renderIngredientItem(item) {
  return `<li class="available-ingredient" data-name="${item.name}" data-id="${item.id}" data-category="${item.category}">${item.name}<div class="ingredient-buttons"><button class="btn btn-add-small add-ingredient-btn" data-name="${item.name}">➕</button><button class="btn btn-favorite favorite-ingredient-btn" data-is-favorite="false" data-ingredient-id="${item.id}">⭐</button></div></li>`;
}

function goBackToCategories() { selectedCategory = null; render(); }

toggleViewBtn.addEventListener("click", () => {
  mode = mode === "list" ? "categories" : "list";
  toggleViewBtn.textContent = mode === "list" ? "Categories" : "List";
  selectedCategory = null;
  render();
});

searchInput.addEventListener("input", render);

allIngredientsList.addEventListener("click", function(event) {
  if (event.target.classList.contains("add-ingredient-btn")) addIngredient(event.target.dataset.name);
  if (event.target.classList.contains("favorite-ingredient-btn")) toggleFavorite(event.target.dataset.ingredientId, event.target.dataset.isFavorite !== "true");
  if (event.target.classList.contains("category-btn")) { selectedCategory = event.target.dataset.catName; render(); }
});

function getCookie(name) {
  return document.cookie.split(';').map(cookie => cookie.trim()).find(cookie => cookie.startsWith(name + "="))?.split('=')[1] || null;
}

document.addEventListener("DOMContentLoaded", () => {
  mode = "list";
  toggleViewBtn.textContent = "Categories";
  render();
  updateSelectedIngredients();
  updateFavoriteIngredientsList();
});
