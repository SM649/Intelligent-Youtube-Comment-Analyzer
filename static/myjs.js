document.addEventListener('DOMContentLoaded', function () {
  const form = document.querySelector('form');
  const loadingSpinner = document.getElementById('loadingSpinner');

  if (form && loadingSpinner) {
      form.addEventListener('submit', function (e) {
          // Keep the spinner logic, actual submission is handled by the browser/backend
          loadingSpinner.style.display = 'flex';
          // The spinner will hide when the new page loads or via backend response handling
      });
  }


});

function toggleClayTheme() {
  var root = document.documentElement;
  var isDark = root.classList.toggle('dark');
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
}