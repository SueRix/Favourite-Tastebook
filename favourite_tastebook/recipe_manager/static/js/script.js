"use strict";

////////////////////////////////////////////////////////////////////////////////
// Global variables and DOM references
////////////////////////////////////////////////////////////////////////////////

let selectedIngredients = [];
let mode = "list";           // can be "list" or "categories"
let selectedCategory = null; // used only in "categories" mode when viewing one category

const searchInput = document.getElementById("semanticSearchInput");
const allIngredientsList = document.querySelector(".all-ingredients-list");
const toggleViewBtn = document.getElementById("toggleView");

// Gather initial ingredient data from HTML (via data attributes)
const ingredientElements = Array.from(document.querySelectorAll(".available-ingredient"));
const ingredientsData = ingredientElements.map(li => ({
  name: li.dataset.name,
  id: li.dataset.id,
  category: li.dataset.category || "Uncategorized"
}));

// Build a unique array of categories
const categories = [...new Set(ingredientsData.map(item => item.category))].sort();

////////////////////////////////////////////////////////////////////////////////
// Selected ingredients: add/remove and update DOM
////////////////////////////////////////////////////////////////////////////////

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
    list.innerHTML = `<li class="no-ingredients">❌ No ingredients selected yet.</li>`;
    return;
  }
  selectedIngredients.forEach(ing => {
    list.innerHTML += `
      <li class="ingredient-item">
        ✅ ${ing}
        <button class="remove-btn" onclick="removeIngredient('${ing}')">✖</button>
      </li>
    `;
  });
}

////////////////////////////////////////////////////////////////////////////////
// Fetching recipes based on selected ingredients
////////////////////////////////////////////////////////////////////////////////

function fetchRecipes() {
  const queryParams = selectedIngredients.join(",");
  const url = `/api/filter_recipes/?ingredients=${encodeURIComponent(queryParams)}`;
  fetch(url)
    .then(response => response.json())
    .then(data => {
      const recipesContainer = document.getElementById("recipes-result");
      recipesContainer.innerHTML = "";
      if (data.recipes && data.recipes.length > 0) {
        data.recipes.forEach(r => {
          recipesContainer.innerHTML += `
            <li>
              <strong>${r.name}</strong> (time: ${r.cook_time || "-" } min)
              <p>${r.instructions || ""}</p>
            </li>
          `;
        });
      } else {
        recipesContainer.innerHTML = "<li>There are no suitable recipes.</li>";
      }
    })
    .catch(err => {
      console.error("Error fetching recipes:", err);
    });
}

////////////////////////////////////////////////////////////////////////////////
// Favorite ingredients: toggle and update
////////////////////////////////////////////////////////////////////////////////

function updateFavoriteIngredientsList() {
  fetch("/api/favorite_ingredient/", {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken")
    }
  })
    .then(response => response.json())
    .then(data => {
      const favoriteIngredientsList = document.querySelector(".favorite-ingredients");
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
      console.error("Error fetching favorite ingredients:", error);
    });
}

function toggleFavorite(ingredientId, add) {
  fetch("/api/favorite_ingredient/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken")
    },
    body: JSON.stringify({
      ingredient_id: ingredientId,
      action: add ? "add" : "remove"
    })
  })
    .then(response => response.json())
    .then(data => {
      if (data.status === "success") {
        updateFavoriteIngredientsList();
      } else {
        console.error("Error toggling favorite:", data.message);
      }
    })
    .catch(error => {
      console.error("Fetch error in toggleFavorite:", error);
    });
}

////////////////////////////////////////////////////////////////////////////////
// Rendering logic: list mode vs. categories mode
////////////////////////////////////////////////////////////////////////////////

function render() {
  // Clear the container
  allIngredientsList.innerHTML = "";

  const searchTerm = searchInput.value.trim().toLowerCase();

  if (mode === "list") {
    // Show ALL ingredients, filtered by searchTerm
    const filtered = ingredientsData.filter(item =>
      item.name.toLowerCase().includes(searchTerm)
    );
    filtered.forEach(item => {
      allIngredientsList.innerHTML += renderIngredientItem(item);
    });
  } else {
    // mode === "categories"
    if (selectedCategory === null) {
      // Show list of categories
      // Optionally filter categories by searchTerm, if desired
      const filteredCats = categories.filter(cat =>
        cat.toLowerCase().includes(searchTerm)
      );
      if (filteredCats.length === 0) {
        allIngredientsList.innerHTML = `<li class="no-ingredients">No categories found.</li>`;
        return;
      }
      filteredCats.forEach(cat => {
        allIngredientsList.innerHTML += renderCategoryItem(cat);
      });
    } else {
      // Show items for the selectedCategory
      const categoryItems = ingredientsData.filter(item =>
        item.category === selectedCategory &&
        item.name.toLowerCase().includes(searchTerm)
      );
      // Optional "Back to categories" link
      allIngredientsList.innerHTML += `
        <li class="ingredient-item">
          <button class="btn" onclick="goBackToCategories()">Back to categories</button>
        </li>
      `;
      if (categoryItems.length === 0) {
        allIngredientsList.innerHTML += `<li class="no-ingredients">No ingredients in this category.</li>`;
        return;
      }
      categoryItems.forEach(item => {
        allIngredientsList.innerHTML += renderIngredientItem(item);
      });
    }
  }
}

// Returns an HTML string for a single ingredient
function renderIngredientItem(item) {
  return `
    <li class="available-ingredient" data-name="${item.name}" data-id="${item.id}" data-category="${item.category}">
      ${item.name}
      <div class="ingredient-buttons">
        <button class="btn btn-add-small add-ingredient-btn" data-name="${item.name}">➕</button>
        <button class="btn btn-favorite favorite-ingredient-btn" data-is-favorite="false" data-ingredient-id="${item.id}">⭐</button>
      </div>
    </li>
  `;
}

// Returns an HTML string for a single category
function renderCategoryItem(catName) {
  return `
    <li class="available-category" data-category="${catName}">
      <button class="btn category-btn" data-cat-name="${catName}">
        ${catName}
      </button>
    </li>
  `;
}

function goBackToCategories() {
  selectedCategory = null;
  render();
}

////////////////////////////////////////////////////////////////////////////////
// Toggle button: switching between "list" and "categories" mode
////////////////////////////////////////////////////////////////////////////////

toggleViewBtn.addEventListener("click", function() {
  if (mode === "list") {
    mode = "categories";
    toggleViewBtn.textContent = "List";
    selectedCategory = null;
  } else {
    mode = "list";
    toggleViewBtn.textContent = "Categories";
    selectedCategory = null;
  }
  render();
});

////////////////////////////////////////////////////////////////////////////////
// Search input listener
////////////////////////////////////////////////////////////////////////////////

searchInput.addEventListener("input", function() {
  render();
});

////////////////////////////////////////////////////////////////////////////////
// Main container click listener: add ingredient, favorite, or pick category
////////////////////////////////////////////////////////////////////////////////

allIngredientsList.addEventListener("click", function(event) {
  // Add to selected
  if (event.target.classList.contains("add-ingredient-btn")) {
    addIngredient(event.target.dataset.name);
  }

  // Toggle favorite
  if (event.target.classList.contains("favorite-ingredient-btn")) {
    const ingredientId = event.target.dataset.ingredientId;
    const isFavorite = event.target.dataset.isFavorite === "true";
    toggleFavorite(ingredientId, !isFavorite);
  }

  // Category clicked
  if (event.target.classList.contains("category-btn")) {
    const catName = event.target.dataset.catName;
    selectedCategory = catName;
    render();
  }
});

////////////////////////////////////////////////////////////////////////////////
// CSRF helper
////////////////////////////////////////////////////////////////////////////////

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      let cookie = cookies[i].trim();
      if (cookie.startsWith(name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

////////////////////////////////////////////////////////////////////////////////
// On DOMContentLoaded, initialize
////////////////////////////////////////////////////////////////////////////////

document.addEventListener("DOMContentLoaded", function() {
  // Start in "list" mode, with button text "Categories"
  mode = "list";
  toggleViewBtn.textContent = "Categories";
  render();

  updateSelectedIngredients();
  updateFavoriteIngredientsList();
});
