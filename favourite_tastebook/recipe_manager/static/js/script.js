function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
const csrftoken = getCookie('csrftoken');

let selectedIngredients = [];

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
  fetch('/api/filter_recipes/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrftoken
    },
    body: JSON.stringify({ ingredients: selectedIngredients })
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

