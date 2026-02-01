import React from 'react';
import { Sidebar } from './components/Sidebar';
import { Workbench } from './components/Workbench';
import { useAppStore } from './store/useAppStore';

function App() {
  const { appState } = useAppStore();
  const showSidebar = appState !== 'RENDERING' && appState !== 'COMPLETED';

  return (
    <div className="flex w-full h-screen overflow-hidden bg-background font-sans text-zinc-900 selection:bg-primary-100 selection:text-primary-900">
      {showSidebar && <Sidebar />}
      <Workbench />
    </div>
  );
}

export default App;
