let selectedIngredients = [];

function addIngredient(ingredientName) {
  if (!selectedIngredients.includes(ingredientName)) {
    selectedIngredients.push(ingredientName);
    updateSelectedIngredients();
  }
}

function removeIngredient(ingredientName) {
  selectedIngredients = selectedIngredients.filter(
    (item) => item !== ingredientName
  );
  updateSelectedIngredients();
}

function updateSelectedIngredients() {
  const list = document.querySelector(".selected-ingredients");
  list.innerHTML = "";

  if (selectedIngredients.length === 0) {
    list.innerHTML = `<li class="no-ingredients">
                        ❌ No ingredients selected yet.
                      </li>`;
  } else {
    selectedIngredients.forEach((ingredient) => {
      list.innerHTML += `
        <li class="ingredient-item">
          ✅ ${ingredient}
          <button
            class="remove-btn"
            onclick="removeIngredient('${ingredient}')"
          >✖</button>
        </li>`;
    });
  }
}

function semanticSearch() {
  const query = document.getElementById("semanticSearchInput").value;
  alert("Performing semantic search for: " + query);
}

function calculate() {
  alert(
    "Calculating recipes based on these ingredients:\n" +
    selectedIngredients.join(", ")
  );
}
