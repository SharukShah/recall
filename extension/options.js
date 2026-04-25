// Options page script for ReCall extension

document.addEventListener('DOMContentLoaded', async () => {
  const form = document.getElementById('settings-form');
  const apiUrlInput = document.getElementById('api-url');
  const authTokenInput = document.getElementById('auth-token');
  const testBtn = document.getElementById('test-connection');
  const status = document.getElementById('status');

  // Load saved settings
  const settings = await chrome.storage.sync.get(['apiUrl', 'authToken']);
  apiUrlInput.value = settings.apiUrl || 'http://localhost:8001';
  authTokenInput.value = settings.authToken || '';

  // Save settings
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    await chrome.storage.sync.set({
      apiUrl: apiUrlInput.value.trim(),
      authToken: authTokenInput.value.trim(),
    });

    showStatus('Settings saved successfully!', 'success');
  });

  // Test connection
  testBtn.addEventListener('click', async () => {
    const apiUrl = apiUrlInput.value.trim();
    const authToken = authTokenInput.value.trim();

    if (!apiUrl) {
      showStatus('Please enter an API URL', 'error');
      return;
    }

    try {
      const headers = { 'Content-Type': 'application/json' };
      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
      }

      const response = await fetch(`${apiUrl}/`, { headers });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      showStatus(`Connection successful! ${data.message || 'Connected to ReCall API'}`, 'success');
    } catch (error) {
      showStatus(`Connection failed: ${error.message}`, 'error');
    }
  });
});

function showStatus(message, type) {
  const status = document.getElementById('status');
  status.textContent = message;
  status.className = type;
  status.style.display = 'block';

  setTimeout(() => {
    status.style.display = 'none';
  }, 5000);
}
