// Popup script for ReCall extension

document.addEventListener('DOMContentLoaded', async () => {
  const settings = await chrome.storage.sync.get(['apiUrl', 'authToken']);
  const apiUrl = settings.apiUrl || 'http://localhost:8001';
  const authToken = settings.authToken || '';

  const notConfiguredDiv = document.getElementById('not-configured');
  const configuredDiv = document.getElementById('configured');
  const connectionStatus = document.getElementById('connection-status');

  if (!authToken) {
    notConfiguredDiv.style.display = 'block';
    configuredDiv.style.display = 'none';
    
    document.getElementById('open-settings').addEventListener('click', () => {
      chrome.runtime.openOptionsPage();
    });
    return;
  }

  notConfiguredDiv.style.display = 'none';
  configuredDiv.style.display = 'block';

  // Test connection and fetch stats
  try {
    const response = await fetch(`${apiUrl}/api/stats/dashboard`, {
      headers: {
        'Authorization': `Bearer ${authToken}`,
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const stats = await response.json();
    connectionStatus.textContent = 'Connected ✓';
    connectionStatus.className = 'status-value success';

    // Update stats
    document.getElementById('items-due').textContent = stats.due_count || 0;
    
    // Get today's captures count
    const capturesResponse = await fetch(`${apiUrl}/api/captures/?limit=100`, {
      headers: {
        'Authorization': `Bearer ${authToken}`,
      },
    });
    
    if (capturesResponse.ok) {
      const captures = await capturesResponse.json();
      const today = new Date().toDateString();
      const todayCaptures = captures.filter(c => 
        new Date(c.created_at).toDateString() === today
      ).length;
      document.getElementById('captures-today').textContent = todayCaptures;
    }

  } catch (error) {
    connectionStatus.textContent = 'Connection Failed ✗';
    connectionStatus.className = 'status-value error';
  }

  // Open dashboard button
  document.getElementById('open-dashboard').addEventListener('click', () => {
    const dashboardUrl = apiUrl.replace(':8001', ':3000').replace(':8000', ':3000');
    chrome.tabs.create({ url: dashboardUrl });
  });

  // Settings button
  document.getElementById('settings-btn').addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });
});
