import { contextBridge } from 'electron';

// Expose protected APIs to renderer via contextBridge
contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  isElectron: true,
});
