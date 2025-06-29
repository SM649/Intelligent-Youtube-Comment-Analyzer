document.addEventListener('DOMContentLoaded', function () {
  // --- Sidebar, Theme, Spinner Logic (from indexupd.html) ---
  const sidebar = document.getElementById('sidebar');
  const content = document.getElementById('content');
  const toggleButton = document.getElementById('sidebarCollapse');
  const closeButton = document.getElementById('sidebarClose');

  if (toggleButton) {
      toggleButton.addEventListener('click', function () {
          sidebar.classList.toggle('collapsed');
          content.classList.toggle('expanded');
      });
  }
  if (closeButton) {
      closeButton.addEventListener('click', function () {
          sidebar.classList.add('collapsed');
          content.classList.remove('expanded'); // Adjust if necessary
      });
  }


  


  

  

  const form = document.querySelector('form');
  const loadingSpinner = document.getElementById('loadingSpinner');

  if (form && loadingSpinner) {
      form.addEventListener('submit', function (e) {
          // Keep the spinner logic, actual submission is handled by the browser/backend
          loadingSpinner.style.display = 'flex';
          // The spinner will hide when the new page loads or via backend response handling
      });
  }


  // --- Percentage Calculation Logic ---
  const summaryContainer = document.getElementById('sentiment-summary');

  if (summaryContainer) { // Check if summaryContainer exists
      const positiveCount = parseInt(summaryContainer.getAttribute('data-positive') || '0', 10);
      const negativeCount = parseInt(summaryContainer.getAttribute('data-negative') || '0', 10);
      const neutralCount = parseInt(summaryContainer.getAttribute('data-neutral') || '0', 10);
      const totalComments = positiveCount + negativeCount + neutralCount;

      function calculateAndUpdate(count, total, percentageElId, countElId, progressElId) {

          const percentageEl = document.getElementById(percentageElId);
          const countEl = document.getElementById(countElId);
          const progressEl = document.getElementById(progressElId);
          let percentage = 0;

          if (total > 0) {
              percentage = Math.round((count / total) * 100);
          }

          if (percentageEl) percentageEl.textContent = `${percentage}%`;
          if (countEl) countEl.textContent = `${count} ${countElId.split('-')[0]} comments detected`; // Assumes ID format 'sentiment-count'
          if (progressEl) {
              progressEl.style.width = `${percentage}%`;
              progressEl.setAttribute('aria-valuenow', percentage);
          }
      }

      calculateAndUpdate(positiveCount, totalComments, 'positive-percentage', 'positive-count', 'positive-progress');
      calculateAndUpdate(negativeCount, totalComments, 'negative-percentage', 'negative-count', 'negative-progress');
      calculateAndUpdate(neutralCount, totalComments, 'neutral-percentage', 'neutral-count', 'neutral-progress');
  } else {
      console.log("Could not find the sentiment-summary container.");
  }

});