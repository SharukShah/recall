// Background service worker for ReCall extension

// Create context menu on installation
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'capture-to-recall',
    title: 'Capture to ReCall',
    contexts: ['selection'],
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'capture-to-recall') {
    const selectedText = info.selectionText;
    if (!selectedText) {
      showNotification('No text selected', 'Please highlight text before using this option.', 'error');
      return;
    }

    // Get settings from storage
    const settings = await chrome.storage.sync.get(['apiUrl', 'authToken']);
    const apiUrl = settings.apiUrl || 'http://localhost:8001';
    const authToken = settings.authToken || '';

    if (!authToken) {
      showNotification('Authentication required', 'Please configure your API token in the extension settings.', 'error');
      chrome.action.openPopup();
      return;
    }

    // Send capture request
    try {
      const response = await fetch(`${apiUrl}/api/captures/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          raw_text: `${tab.title}\n\n${selectedText}`,
          source_type: 'extension',
          source_url: tab.url,
          why_it_matters: null,
        }),
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication failed. Check your API token.');
        }
        throw new Error(`Capture failed: ${response.statusText}`);
      }

      const data = await response.json();
      const factCount = data.extracted_facts?.length || 0;
      
      showNotification(
        'Captured!',
        `${factCount} facts extracted from: "${selectedText.substring(0, 50)}..."`,
        'success'
      );

      // Update badge
      chrome.action.setBadgeText({ text: '+1' });
      chrome.action.setBadgeBackgroundColor({ color: '#10b981' });
      setTimeout(() => {
        chrome.action.setBadgeText({ text: '' });
      }, 3000);

    } catch (error) {
      showNotification('Capture failed', error.message || 'Check your connection and settings.', 'error');
    }
  }
});

// Show notification
function showNotification(title, message, type) {
  chrome.notifications.create({
    type: 'basic',
    iconUrl: 'icons/icon48.png',
    title: title,
    message: message,
    priority: type === 'error' ? 2 : 1,
  });
}

// Listen for messages from content script or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'capture') {
    // Handle capture request from content script
    handleCapture(request.text, request.title, request.url)
      .then(result => sendResponse({ success: true, result }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; // Keep channel open for async response
  }
});

async function handleCapture(text, title, url) {
  const settings = await chrome.storage.sync.get(['apiUrl', 'authToken']);
  const apiUrl = settings.apiUrl || 'http://localhost:8001';
  const authToken = settings.authToken || '';

  if (!authToken) {
    throw new Error('Authentication required');
  }

  const response = await fetch(`${apiUrl}/api/captures/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`,
    },
    body: JSON.stringify({
      raw_text: `${title}\n\n${text}`,
      source_type: 'extension',
      source_url: url,
      why_it_matters: null,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return await response.json();
}
