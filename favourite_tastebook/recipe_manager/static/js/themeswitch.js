document.addEventListener('DOMContentLoaded', function () {
  const darkBtn  = document.getElementById('darkModeBtn');
  const lightBtn = document.getElementById('lightModeBtn');

  if (darkBtn)  darkBtn.addEventListener('click', function () {
    document.body.classList.add('dark-mode');
    document.body.classList.remove('light-mode');
  });

  if (lightBtn) lightBtn.addEventListener('click', function () {
    document.body.classList.add('light-mode');
    document.body.classList.remove('dark-mode');
  });
});
