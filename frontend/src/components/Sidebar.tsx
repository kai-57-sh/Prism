import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, User, Bot } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import { api } from '../api/client';
import clsx from 'clsx';
import { motion } from 'framer-motion';

export const Sidebar = () => {
  const { messages, addMessage, setAppState, appState, setCurrentJobId, setScript, setShotPlan, setShotAssets, currentJobId } = useAppStore();
  const [input, setInput] = useState('');
  const [selectedStyle, setSelectedStyle] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const styleOptions = [
    { label: '扁平插画', promptValue: '扁平插画' },
    { label: '3D 卡通', promptValue: '3D卡通' },
    { label: '真人实拍', promptValue: '真人实拍' },
    { label: 'MG 动画', promptValue: 'MG动画' },
  ];

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, appState]);

  const pollJobStatus = async (jobId: string) => {
      const interval = setInterval(async () => {
          try {
              const status = await api.getJobStatus(jobId);
              
              if (status.status === 'SUCCEEDED') {
                  clearInterval(interval);
                  if (status.assets && status.assets.length > 0) {
                      setShotAssets(status.assets);
                      setAppState('COMPLETED');
                      addMessage('ai', '视频生成完成！请在右侧查看。');
                  } else {
                      setAppState('EDITING');
                      addMessage('ai', '视频脚本和分镜生成完毕！请查看右侧工作区。');
                  }
                  if (status.script) setScript(status.script);
                  
                  // Handle shot_plan structure
                  if (status.shot_plan && status.shot_plan.shots) {
                      setShotPlan(status.shot_plan.shots);
                  }
              } else if (status.status === 'FAILED') {
                  clearInterval(interval);
                  setAppState('IDLE'); // Or error state
                  addMessage('ai', `生成失败: ${status.error?.message || '未知错误'}`);
              } else if (status.status === 'RUNNING') {
                   // Optional: Update progress or keep 'THINKING'/'GENERATING'
                   if (status.script && appState !== 'GENERATING') {
                       setAppState('GENERATING'); // Switch to generating view once we have some data if supported
                   }
              }
          } catch (e) {
              console.error("Polling error", e);
              // Don't clear interval immediately on network error, maybe retry
          }
      }, 2000);
  };

  const handleSend = async () => {
    if (!input.trim()) return;
    if (input.trim().length < 2) {
        addMessage('ai', '请至少输入 2 个字符的描述。');
        return;
    }
    const userInput = input;
    const stylePrompt = selectedStyle ? `\n风格：${selectedStyle}` : '';
    const promptWithStyle = `${userInput}${stylePrompt}`;
    addMessage('user', promptWithStyle);
    setInput('');
    
    if (appState === 'IDLE' || appState === 'COMPLETED') {
      setAppState('THINKING');
      try {
          const res = await api.planVideo({
              user_prompt: promptWithStyle,
              quality_mode: 'balanced',
              resolution: '1280x720'
          });
          
          setCurrentJobId(res.job_id);
          addMessage('ai', '好的，正在为您生成脚本和分镜...');
          
          // Start polling
          pollJobStatus(res.job_id);
          
      } catch (e: any) {
          setAppState('IDLE');
          addMessage('ai', `抱歉，提交任务失败: ${e.message}`);
      }

    } else if (appState === 'EDITING' && currentJobId) {
       // Revise logic
       setAppState('THINKING');
       try {
           const res = await api.reviseVideo(currentJobId, promptWithStyle);
           setCurrentJobId(res.job_id); // Update to new revision job id
           addMessage('ai', '收到修改意见，正在重新生成...');
           pollJobStatus(res.job_id);
       } catch (e: any) {
           setAppState('EDITING');
           addMessage('ai', `修改请求失败: ${e.message}`);
       }
    }
  };


  return (
    <div className="w-96 h-screen bg-white border-r border-zinc-200 flex flex-col flex-shrink-0 z-10 shadow-sm">
      <div className="p-4 border-b border-zinc-100 flex items-center gap-2 bg-white">
        <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center text-white font-bold shadow-sm shadow-primary-200">
          <Sparkles size={18} />
        </div>
        <span className="font-semibold text-zinc-800 tracking-tight">HealthCanvas AI</span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-5 bg-zinc-50/50" ref={scrollRef}>
        {messages.map((msg, idx) => (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            key={idx} 
            className={clsx("flex gap-3", msg.role === 'user' ? "flex-row-reverse" : "")}
          >
            <div className={clsx(
              "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 border",
              msg.role === 'ai' ? "bg-white border-zinc-200 text-primary-600" : "bg-white border-zinc-200 text-zinc-600"
            )}>
              {msg.role === 'ai' ? <Bot size={16} /> : <User size={16} />}
            </div>
            <div className={clsx(
              "p-3 rounded-2xl max-w-[85%] text-sm leading-relaxed shadow-sm",
              msg.role === 'ai' ? "bg-white border border-zinc-100 text-zinc-700" : "bg-primary-600 text-white"
            )}>
              {msg.content}
            </div>
          </motion.div>
        ))}
        {appState === 'THINKING' && (
             <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex gap-3"
             >
                <div className="w-8 h-8 rounded-full bg-white border border-zinc-200 text-primary-600 flex items-center justify-center flex-shrink-0">
                  <Bot size={16} />
                </div>
                <div className="p-3 rounded-2xl bg-white border border-zinc-100 text-zinc-500 text-sm italic flex items-center gap-2 shadow-sm">
                  <Sparkles size={14} className="animate-spin text-primary-500" /> 正在思考创意...
                </div>
             </motion.div>
        )}
      </div>

      <div className="p-4 border-t border-zinc-100 bg-white">
         <div className="flex gap-2 mb-3 overflow-x-auto pb-2 scrollbar-hide no-scrollbar">
            {styleOptions.map((style) => {
              const isSelected = selectedStyle === style.promptValue;
              return (
                <button
                  key={style.label}
                  onClick={() => setSelectedStyle(isSelected ? null : style.promptValue)}
                  className={clsx(
                    "px-3 py-1 border rounded-full text-xs whitespace-nowrap transition-all duration-200",
                    isSelected
                      ? "bg-green-50 border-green-200 text-green-700"
                      : "bg-zinc-50 border-zinc-200 text-zinc-600 hover:bg-primary-50 hover:text-primary-600 hover:border-primary-200"
                  )}
                >
                  {style.label}
                </button>
              );
            })}
         </div>
        <div className="relative group">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSend())}
            placeholder="描述你想生成的视频内容..."
            className="w-full p-3 pr-12 bg-zinc-50 border border-zinc-200 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 text-sm h-24 transition-all duration-200 group-hover:bg-white group-hover:shadow-sm"
          />
          <div className="absolute bottom-3 right-3 flex gap-2">
             <button 
                onClick={handleSend} 
                disabled={!input.trim()}
                className="p-1.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:hover:bg-primary-600 transition-all shadow-sm shadow-primary-200"
             >
                <Send size={16} />
             </button>
          </div>
        </div>
      </div>
    </div>
  );
};
