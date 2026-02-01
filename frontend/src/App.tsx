import React, { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { Workbench } from './components/Workbench';
import { useAppStore } from './store/useAppStore';
import { AUTH_STORAGE_KEY, LoginGate } from './components/LoginGate';

function App() {
  const { appState } = useAppStore();
  const [isAuthed, setIsAuthed] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.localStorage.getItem(AUTH_STORAGE_KEY) === '1';
  });
  const showSidebar = appState !== 'RENDERING' && appState !== 'COMPLETED';

  if (!isAuthed) {
    return <LoginGate onSuccess={() => setIsAuthed(true)} />;
  }

  return (
    <div className="flex w-full h-screen overflow-hidden bg-background font-sans text-zinc-900 selection:bg-primary-100 selection:text-primary-900">
      {showSidebar && <Sidebar />}
      <Workbench />
    </div>
  );
}

export default App;
