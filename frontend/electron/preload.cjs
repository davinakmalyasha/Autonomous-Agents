const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('antigravity', {
  /** Open a native folder picker dialog. Returns the selected path or null. */
  selectFolder: () => ipcRenderer.invoke('select-folder'),
});
