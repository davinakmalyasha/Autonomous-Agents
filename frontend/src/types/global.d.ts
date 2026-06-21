export {};

declare global {
  interface Window {
    antigravity?: {
      /** Open a native folder picker dialog (Electron). Returns path or null. */
      selectFolder: () => Promise<string | null>;
    };
    /** Browser File System Access API */
    showDirectoryPicker?: () => Promise<FileSystemDirectoryHandle>;
  }
}
