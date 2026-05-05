/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Default API base URL. Leave blank to use the same origin. */
  readonly VITE_API_BASE_URL?: string;
  /** Default API key sent as `X-API-Key`. Overridden by anything set in the Settings UI. */
  readonly VITE_API_KEY?: string;
  /** Local-dev only: backend port the Vite proxy targets (defaults to 8000). */
  readonly VITE_BACKEND_PORT?: string;
  /** Local-dev only: full backend URL the Vite proxy targets. Overrides `VITE_BACKEND_PORT`. */
  readonly VITE_BACKEND_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
