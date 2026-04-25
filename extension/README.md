# ReCall Browser Extension

Chrome extension for capturing highlighted text from any webpage directly to your ReCall spaced repetition system.

## Features

- **Right-click to capture**: Highlight text, right-click, select "Capture to ReCall"
- **Automatic extraction**: Backend automatically extracts facts and generates review questions
- **Connection status**: Popup shows API connection status and today's capture count
- **Configurable**: Set custom API URL and authentication token

## Installation

### Option 1: Load as Unpacked Extension (Development)

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `extension/` directory from your ReCall project
5. The extension icon should appear in your toolbar

### Option 2: Pack and Install

1. In Chrome, go to `chrome://extensions/`
2. Click "Pack extension"
3. Select the `extension/` directory
4. Chrome will create a `.crx` file
5. Drag and drop the `.crx` file onto the extensions page

## Configuration

1. Click the ReCall extension icon in your toolbar
2. Click "Open Settings" (or right-click the icon → Options)
3. Configure:
   - **API URL**: Where your backend is running (default: `http://localhost:8001`)
   - **Auth Token**: Your API token (leave empty if auth is disabled)
4. Click "Save Settings"
5. Click "Test Connection" to verify

## Usage

1. **Capture text from any webpage:**
   - Highlight the text you want to capture
   - Right-click
   - Select "Capture to ReCall"
   - Wait for success notification

2. **Check your captures:**
   - Click the extension icon to see today's capture count
   - Click "Open Dashboard" to view all captures in ReCall

## Troubleshooting

### "Authentication required" error
- Make sure you've set your auth token in the extension settings
- Verify the token matches your backend configuration

### "Connection failed" error
- Check that your ReCall backend is running
- Verify the API URL in settings matches your backend URL
- Check Chrome DevTools console for detailed errors

### Context menu doesn't appear
- Make sure you have text highlighted when right-clicking
- Try reloading the extension: `chrome://extensions/` → click reload icon

## Development

### File Structure

```
extension/
├── manifest.json      # Extension manifest (Chrome v3)
├── background.js      # Service worker (handles captures)
├── content.js         # Content script (runs on pages)
├── popup.html         # Extension popup UI
├── popup.js           # Popup logic
├── popup.css          # Popup styling
├── options.html       # Settings page UI
├── options.js         # Settings logic
└── icons/             # Extension icons
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```

### Permissions

- `contextMenus`: Create "Capture to ReCall" menu item
- `storage`: Save API URL and auth token
- `notifications`: Show capture success/failure notifications
- `host_permissions`: Access to your ReCall API URLs

## Privacy

- The extension only sends data to the URL you configure
- No data is sent to third parties
- Authentication tokens are stored securely in Chrome's sync storage
- Captured text is only sent when you explicitly right-click → capture

## Support

For issues or feature requests, check the main ReCall documentation at `docs/` in the project repository.
