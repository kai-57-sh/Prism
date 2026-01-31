import React from 'react';
import { Sidebar } from './components/Sidebar';
import { Workbench } from './components/Workbench';

function App() {
  return (
    <div className="flex w-full h-screen overflow-hidden bg-background font-sans text-zinc-900 selection:bg-primary-100 selection:text-primary-900">
      <Sidebar />
      <Workbench />
    </div>
  );
}

export default App;
