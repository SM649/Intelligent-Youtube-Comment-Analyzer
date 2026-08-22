document.addEventListener('DOMContentLoaded', function () {
  const form = document.querySelector('form');
  const loadingSpinner = document.getElementById('loadingSpinner');
  const loadingStageText = document.getElementById('loadingStageText');
  const loadingStages = ['Fetching comments...', 'Analyzing sentiment...', 'Extracting topics...', 'Summarizing...'];

  if (form && loadingSpinner) {
      form.addEventListener('submit', function (e) {
          // Keep the spinner logic, actual submission is handled by the browser/backend
          loadingSpinner.style.display = 'flex';
          // The spinner will hide when the new page loads or via backend response handling
          if (loadingStageText) {
              let stageIndex = 0;
              loadingStageText.textContent = loadingStages[stageIndex];
              setInterval(function () {
                  stageIndex = (stageIndex + 1) % loadingStages.length;
                  loadingStageText.textContent = loadingStages[stageIndex];
              }, 1500);
              // No clearInterval call: the page navigates away on the form's normal
              // submit/response cycle, which discards this interval along with the page.
          }
      });
  }


});

function toggleClayTheme() {
  var root = document.documentElement;
  var isDark = root.classList.toggle('dark');
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
}