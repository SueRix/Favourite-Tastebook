let selectedIngredients = [];

function addIngredient(name) {
  if (!selectedIngredients.includes(name)) {
    selectedIngredients.push(name);
    updateSelectedIngredients();
    fetchRecipes();
  }
}

//TODO: recreate code using a fixed FilterRecipe django view.

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
  // Build a query string like ?ingredients=tomato,onion
  const queryParams = selectedIngredients.join(',');
  const url = `/api/filter_recipes/?ingredients=${encodeURIComponent(queryParams)}`;

  // For GET requests, we don't need the CSRF token in headers by default
  // (unless your middleware is configured differently).
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