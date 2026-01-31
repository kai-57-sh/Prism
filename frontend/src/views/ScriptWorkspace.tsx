import React, { useEffect, useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import { CheckCircle2, Circle, Loader2, Play, Image as ImageIcon, Upload, RefreshCw } from 'lucide-react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

export const ScriptWorkspace = () => {
  const { appState, setAppState, script, setScript, appendScript, addMessage, shotPlan } = useAppStore();
  const [activeStep, setActiveStep] = useState(0);
  const [uploadedScenes, setUploadedScenes] = useState<Record<number, boolean>>({});

  // Auto-progress logic based on appState
  useEffect(() => {
    if (appState === 'GENERATING') {
      setActiveStep(1);
      // NOTE: Script is now appended via Sidebar polling mechanism, not simulated here.
      // We just watch for appState changes.
    } else if (appState === 'THINKING') {
      setActiveStep(0);
    } else if (appState === 'EDITING') {
        setActiveStep(2); 
    }
  }, [appState]);

  const handleGenerateVideo = () => {
    setAppState('RENDERING');
    // In real app, this would trigger final rendering job or simply navigate to VideoView 
    // if assets are already ready (which they are in our current backend flow).
    // For now, we simulate a short loading to switch view.
    setTimeout(() => {
        setAppState('COMPLETED');
    }, 1500);
  };

  const handleCardClick = (index: number) => {
    // Add revision context to the chat
    addMessage('ai', `已选中场景 ${index}。如果您对这个分镜的画面或旁白不满意，请直接告诉我您想如何修改，我会帮您更新。`);
  };

  const handleUpload = (index: number) => {
    // TODO: Implement actual file upload to backend
    // Currently backend doesn't support image inputs for revision.
    // Future plan: Add /upload endpoint, return URL, and pass to revise API.
    alert("目前后端暂不支持自定义素材上传，仅支持文本微调。该功能将在后续版本开放。");
    // setUploadedScenes(prev => ({ ...prev, [index]: true }));
    // addMessage('ai', `收到，已为场景 ${index} 替换了您上传的素材。`);
  };

  return (
    <div className="flex h-full">
      {/* Left Task Progress Panel */}
      <div className="w-64 bg-white border-r border-zinc-200 p-6 flex flex-col">
        <h2 className="font-semibold text-zinc-800 mb-6">任务进度</h2>
        <div className="space-y-6 relative">
          <div className="absolute left-3.5 top-2 bottom-2 w-0.5 bg-zinc-100 -z-10"></div>
          <StepItem 
            status={activeStep > 0 ? 'completed' : activeStep === 0 ? 'loading' : 'pending'} 
            title="脚本构思" 
            desc="AI 正在分析需求..." 
          />
          <StepItem 
            status={activeStep > 1 ? 'completed' : activeStep === 1 ? 'loading' : 'pending'} 
            title="分镜生成" 
            desc="绘制视觉草图..." 
          />
          <StepItem 
            status={activeStep > 2 ? 'completed' : activeStep === 2 ? 'loading' : 'pending'} 
            title="准备就绪" 
            desc="等待人工确认" 
          />
        </div>
        
        {appState === 'EDITING' && (
             <motion.button
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                onClick={handleGenerateVideo}
                className="mt-auto w-full py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-xl font-medium shadow-lg shadow-primary-200 flex items-center justify-center gap-2"
             >
                <Play size={18} fill="currentColor" /> 生成视频
             </motion.button>
        )}
      </div>

      {/* Right Editor Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-zinc-50/50">
        <div className="flex-1 p-6 flex gap-6 overflow-hidden">
            {/* Script Editor */}
            <div className="w-1/2 bg-white rounded-2xl border border-zinc-200 shadow-sm flex flex-col overflow-hidden">
                <div className="p-4 border-b border-zinc-100 bg-zinc-50 flex justify-between items-center">
                    <span className="font-medium text-zinc-700 flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-primary-500"></span> 脚本编辑器
                    </span>
                    <span className="text-xs text-zinc-400">Read-only mode</span>
                </div>
                <div className="flex-1 p-4 overflow-y-auto font-mono text-sm leading-loose">
                    {script ? (
                        script.split('\n').map((line, i) => (
                            <div key={i} className={clsx(
                                "py-1 px-2 rounded hover:bg-zinc-50 transition-colors",
                                line.startsWith('[') ? "text-primary-600 font-semibold" : 
                                line.startsWith('旁白') ? "text-zinc-600 pl-4" : "text-zinc-800"
                            )}>
                                {line}
                            </div>
                        ))
                    ) : (
                        <div className="h-full flex items-center justify-center text-zinc-300 italic">
                            等待生成...
                        </div>
                    )}
                </div>
            </div>

            {/* Visual Storyboard */}
            <div className="w-1/2 flex flex-col gap-4 overflow-y-auto pr-2">
                 <h3 className="font-medium text-zinc-700">分镜预览</h3>
                 <div className="grid grid-cols-1 gap-4">
                    {shotPlan ? (
                        shotPlan.map((shot, i) => (
                            <StoryboardCard 
                                key={shot.shot_id || i} 
                                index={i + 1} 
                                shot={shot}
                                isVisible={true} 
                                onClick={() => handleCardClick(i + 1)}
                                onUpload={() => handleUpload(i + 1)}
                                hasUpload={uploadedScenes[i + 1]}
                            />
                        ))
                    ) : (
                        [1, 2, 3].map(i => (
                             <StoryboardCard 
                                key={i} 
                                index={i} 
                                shot={null}
                                isVisible={activeStep >= 1} 
                                onClick={() => {}}
                                onUpload={() => {}}
                                hasUpload={false}
                            />
                        ))
                    )}
                 </div>
            </div>
        </div>
      </div>
    </div>
  );
};

const StepItem = ({ status, title, desc }: { status: 'pending' | 'loading' | 'completed', title: string, desc: string }) => {
    return (
        <div className="flex gap-4">
            <div className="relative flex-shrink-0">
                {status === 'completed' && <CheckCircle2 className="text-primary-600 bg-white" size={28} />}
                {status === 'loading' && <Loader2 className="text-primary-600 animate-spin bg-white" size={28} />}
                {status === 'pending' && <Circle className="text-zinc-300 bg-white" size={28} />}
            </div>
            <div>
                <h3 className={clsx("font-medium", status === 'pending' ? "text-zinc-400" : "text-zinc-800")}>{title}</h3>
                <p className="text-xs text-zinc-500">{desc}</p>
            </div>
        </div>
    )
}

const StoryboardCard = ({ index, shot, isVisible, onClick, onUpload, hasUpload }: { index: number, shot: any, isVisible: boolean, onClick: () => void, onUpload: () => void, hasUpload: boolean }) => {
    return (
        <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: isVisible ? 1 : 0.5, scale: isVisible ? 1 : 0.95 }}
            onClick={onClick}
            className="bg-white rounded-xl border border-zinc-200 p-3 shadow-sm flex gap-4 h-32 group hover:border-primary-300 transition-all cursor-pointer ring-offset-2 focus:ring-2"
        >
            <div className="w-40 bg-zinc-100 rounded-lg flex items-center justify-center text-zinc-300 relative overflow-hidden group-hover:bg-zinc-50">
                {isVisible ? (
                    hasUpload ? (
                        <div className="w-full h-full bg-teal-100 flex items-center justify-center text-teal-600 relative">
                             <span className="font-semibold text-xs">用户上传素材</span>
                             <span className="absolute bottom-2 right-2 text-xs font-mono text-teal-600/50">SCENE {index}</span>
                        </div>
                    ) : (
                     <div className="w-full h-full bg-primary-50 flex items-center justify-center text-primary-300">
                        <ImageIcon size={32} />
                        <span className="absolute bottom-2 right-2 text-xs font-mono text-primary-400/50">SCENE {index}</span>
                     </div>
                    )
                ) : (
                    <Loader2 className="animate-spin" />
                )}
            </div>
            <div className="flex-1 flex flex-col justify-between py-1">
                <div>
                    <div className="flex justify-between items-start mb-2">
                        <span className="text-xs font-bold text-zinc-400">SCENE {index}</span>
                        <button className="p-1 hover:bg-zinc-100 rounded text-zinc-400"><RefreshCw size={14} /></button>
                    </div>
                    <p className="text-xs text-zinc-600 line-clamp-3">
                        {shot ? (shot.visual_prompt || shot.narration) : "Waiting for generation..."}
                    </p>
                </div>
                <div className="flex justify-end">
                    <button className="text-xs flex items-center gap-1 text-zinc-400 hover:text-primary-600 transition-colors" onClick={(e) => { e.stopPropagation(); onUpload(); }}>
                        <Upload size={12} /> 替换素材
                    </button>
                </div>
            </div>
        </motion.div>
    )
}

