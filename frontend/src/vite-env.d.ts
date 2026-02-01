/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_LOGIN_PASSWORD?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
