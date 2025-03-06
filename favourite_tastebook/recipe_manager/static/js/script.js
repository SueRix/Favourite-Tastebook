let selectedIngredients = [];
const searchInput = document.getElementById('semanticSearchInput');
const allIngredientsList = document.querySelector('.all-ingredients-list');
const ingredients = Array.from(document.querySelectorAll('.available-ingredient')).map(li => li.dataset.name);

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
  const filteredIngredients = ingredients.filter(ingredient =>
    ingredient.toLowerCase().includes(searchTerm.toLowerCase())
  );
  filteredIngredients.forEach(ingredient => {
    allIngredientsList.innerHTML += `
      <li class="available-ingredient" data-name="${ingredient}">
        ${ingredient}
        <button class="btn btn-add-small" data-name="${ingredient}">➕</button>
      </li>
    `;
  });
}

searchInput.addEventListener('input', function() {
  filterIngredients(this.value);
});

allIngredientsList.addEventListener('click', function(event) {
  if (event.target.classList.contains('btn-add-small')) {
    addIngredient(event.target.dataset.name);
  }
});

filterIngredients('');