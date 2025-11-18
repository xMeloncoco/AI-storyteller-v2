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

// Disable hardware acceleration to prevent GPU crashes on Windows
// This fixes the "GPU process exited unexpectedly" error
app.disableHardwareAcceleration();

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
