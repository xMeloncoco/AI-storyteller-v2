/**
 * Dreamwalkers - Main Electron Process
 *
 * This file creates the main application window and handles
 * communication between the renderer process and the system.
 */
const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');

// Keep a global reference of the window object
let mainWindow;

// GPU stability vs. input focus trade-off (Windows):
//
// We previously called app.disableHardwareAcceleration() to stop the
// "GPU process exited unexpectedly" crash. But on Windows that forces
// software compositing, which triggers a Chromium bug where <input>/
// <textarea> fields intermittently stop accepting focus/typing (you click
// and nothing happens). It affects every text field in the app.
//
// Instead, keep hardware acceleration ON but route GPU work through ANGLE's
// software GL backend. That avoids the GPU-process crash on flaky drivers
// without dropping to the full software-compositing path that breaks inputs.
// If a machine still crashes, set DREAMWALKERS_DISABLE_GPU=1 to fall back to
// the old behavior.
if (process.env.DREAMWALKERS_DISABLE_GPU === '1') {
    app.disableHardwareAcceleration();
} else {
    app.commandLine.appendSwitch('use-angle', 'swiftshader');
}

function createWindow() {
    // Create the browser window
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1000,
        minHeight: 700,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false, // Note: For production, consider enabling this
            enableRemoteModule: true
        },
        title: 'Dreamwalkers - AI Storytelling',
        backgroundColor: '#1a1a2e'
    });

    // Load the index.html file
    mainWindow.loadFile('src/index.html');

    // Open DevTools in development mode
    if (process.argv.includes('--dev')) {
        mainWindow.webContents.openDevTools();
    }

    // Handle window close
    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    // Log when window is ready
    mainWindow.webContents.on('did-finish-load', () => {
        console.log('Dreamwalkers window loaded successfully');
    });
}

// Create window when app is ready
app.whenReady().then(createWindow);

// Quit when all windows are closed
app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// On macOS, recreate window when dock icon is clicked
app.on('activate', () => {
    if (mainWindow === null) {
        createWindow();
    }
});

// Handle any IPC messages from renderer
ipcMain.on('app-info', (event) => {
    event.reply('app-info-response', {
        version: app.getVersion(),
        platform: process.platform
    });
});

console.log('Dreamwalkers main process started');
