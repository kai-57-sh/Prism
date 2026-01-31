import React from 'react';
import { useAppStore } from '../store/useAppStore';
import { LandingView } from '../views/LandingView';
import { ScriptWorkspace } from '../views/ScriptWorkspace';
import { VideoView } from '../views/VideoView';
import { AnimatePresence, motion } from 'framer-motion';

export const Workbench = () => {
  const { appState } = useAppStore();

  const renderView = () => {
    switch (appState) {
      case 'IDLE':
        return <LandingView />;
      case 'THINKING':
      case 'GENERATING':
      case 'EDITING':
      case 'RENDERING':
        return <ScriptWorkspace />;
      case 'COMPLETED':
        return <VideoView />;
      default:
        return <LandingView />;
    }
  };

  return (
    <div className="flex-1 bg-background h-screen overflow-hidden flex flex-col relative">
      <AnimatePresence mode="wait">
        <motion.div
            key={appState === 'IDLE' ? 'idle' : appState === 'COMPLETED' ? 'completed' : 'workspace'}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
            className="w-full h-full"
        >
            {renderView()}
        </motion.div>
      </AnimatePresence>
    </div>
  );
};
