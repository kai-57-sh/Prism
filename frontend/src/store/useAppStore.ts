import { create } from 'zustand';
import { api, JobStatusResponse } from '../api/client';

export type AppState = 'IDLE' | 'THINKING' | 'GENERATING' | 'EDITING' | 'RENDERING' | 'COMPLETED';

interface StoreState {
  appState: AppState;
  setAppState: (state: AppState) => void;
  messages: Array<{role: 'user' | 'ai', content: string}>;
  addMessage: (role: 'user' | 'ai', content: string) => void;
  
  // Job Data
  currentJobId: string | null;
  setCurrentJobId: (id: string | null) => void;
  
  // Script & Assets
  script: string;
  setScript: (script: string) => void;
  appendScript: (chunk: string) => void;
  
  shotPlan: Array<any> | undefined; // Simplified for now, or define Shot interface
  setShotPlan: (plan: Array<any> | undefined) => void;

  shotAssets: Array<any> | undefined;
  setShotAssets: (assets: Array<any> | undefined) => void;
  updateShotDuration: (index: number, duration: number) => void;
}

export const useAppStore = create<StoreState>((set) => ({
  appState: 'IDLE',
  setAppState: (state) => set({ appState: state }),
  messages: [
    { role: 'ai', content: '你好！我是你的健康视频助手。今天想制作什么样的科普视频？' }
  ],
  addMessage: (role, content) => set((state) => ({ messages: [...state.messages, { role, content }] })),
  
  currentJobId: null,
  setCurrentJobId: (id) => set({ currentJobId: id }),

  script: '',
  setScript: (script) => set({ script }),
  appendScript: (chunk) => set((state) => ({ script: state.script + chunk })),

  shotPlan: undefined,
  setShotPlan: (plan) => set({ shotPlan: plan }),

  shotAssets: undefined,
  setShotAssets: (assets) => set({ shotAssets: assets }),
  updateShotDuration: (index, duration) => set((state) => {
      if (!state.shotAssets) return {};
      const newAssets = [...state.shotAssets];
      if (newAssets[index]) {
          newAssets[index] = { ...newAssets[index], duration_s: duration };
      }
      return { shotAssets: newAssets };
  }),
}));

