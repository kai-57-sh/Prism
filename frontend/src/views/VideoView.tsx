import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, SkipBack, SkipForward, Volume2, Settings, Download, Share2, MessageSquare } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import { VideoTrackItem, AudioTrackItem } from '../components/TimelineTracks';

export const VideoView = () => {
  const { shotAssets, updateShotDuration } = useAppStore();
  const [isPlaying, setIsPlaying] = useState(false);
  const [activeShotIndex, setActiveShotIndex] = useState(0);
  const videoRef = useRef<HTMLVideoElement>(null);
  const pendingSeekTimeRef = useRef<number | null>(null);

  // Use the first generated video if available, or fallback to mock
  const currentVideoUrl = shotAssets && shotAssets.length > 0 ? shotAssets[activeShotIndex].video_url : "";
  const isVideo = shotAssets && shotAssets.length > 0;

  // Placeholder images for filmstrip effect - using colored placeholders to avoid CORB
  const getPlaceholderStyle = (index: number) => {
      const colors = ['#3f51b5', '#009688', '#ff5722', '#795548', '#607d8b'];
      return { backgroundColor: colors[index % colors.length] };
  };

  const handleVideoEnded = () => {
      // Auto-advance to next shot if available
      if (shotAssets && activeShotIndex < shotAssets.length - 1) {
          setActiveShotIndex(prev => prev + 1);
          // Keep playing state true so next video plays automatically
      } else {
          setIsPlaying(false);
          setActiveShotIndex(0); // Loop back to start or stop
      }
  };

  const totalDuration = shotAssets ? shotAssets.reduce((acc, shot) => acc + (shot.duration_s || 5), 0) : 20;
  // Get duration of current active shot from metadata (fallback)
  const plannedShotDuration = shotAssets && shotAssets.length > 0 ? (shotAssets[activeShotIndex].duration_s || 5) : 5;
  
  const [globalTime, setGlobalTime] = useState(0);
  // State for current shot local time for the progress bar
  const [localTime, setLocalTime] = useState(0);
  // State for actual video duration
  const [realVideoDuration, setRealVideoDuration] = useState(plannedShotDuration);
  const [isDragging, setIsDragging] = useState(false);
  const lastSeekTimeRef = useRef(0);
  const playheadRef = useRef<HTMLDivElement>(null);

  // Reset real duration when shot changes
  useEffect(() => {
      setRealVideoDuration(plannedShotDuration);
  }, [activeShotIndex, plannedShotDuration]);

  // Sync global time with video play
  useEffect(() => {
    let interval: any;
    if (isPlaying) {
      interval = setInterval(() => {
        setGlobalTime(prev => {
           // Calculate time offset for current shot
           const currentShotStart = shotAssets?.slice(0, activeShotIndex).reduce((acc, s) => acc + (s.duration_s || 5), 0) || 0;
           // If video ref is playing, use its current time
           if (videoRef.current) {
               const currentTime = videoRef.current.currentTime;
               setLocalTime(currentTime); // Update local time state
               const newGlobal = currentShotStart + currentTime;
               
               // Check if we reached the end of the ACTUAL video or the PLANNED duration
               // Usually onEnded handles the actual video end.
               // But if planned duration is shorter than video, we might want to cut it? 
               // For now, let's just let onEnded handle the transition to keep it simple.
               
               return newGlobal;
           }
           return prev;
        });
      }, 100);
    } else {
        // When paused, still update local time if video ref exists (e.g. after seeking)
        if (videoRef.current) {
            setLocalTime(videoRef.current.currentTime);
        }
    }
    return () => clearInterval(interval);
  }, [isPlaying, activeShotIndex, shotAssets, totalDuration]);

  // Update local time when active shot changes or global time is set manually
  useEffect(() => {
       const currentShotStart = shotAssets?.slice(0, activeShotIndex).reduce((acc, s) => acc + (s.duration_s || 5), 0) || 0;
       const local = Math.max(0, globalTime - currentShotStart);
       // We don't clamp to realVideoDuration here strictly because global time might be in the "gap"
       // But for the local time display, it makes sense to clamp to what's playable
       // However, if we are in the "gap" (video ended, but slot continues), local time should probably just stay at max video duration
       setLocalTime(local); 
  }, [globalTime, activeShotIndex, shotAssets]);

  useEffect(() => {
    if (videoRef.current) {
        if (isPlaying) {
            videoRef.current.play().catch(e => console.error("Play error:", e));
        } else {
            videoRef.current.pause();
        }
    }
  }, [isPlaying, currentVideoUrl]); // React to play state change and video source change

  const handleVideoDurationChange = (e: React.SyntheticEvent<HTMLVideoElement>) => {
      const vid = e.currentTarget;
      if (vid.duration && !isNaN(vid.duration)) {
          console.log(`[VideoView] Shot ${activeShotIndex} duration loaded: ${vid.duration}s. Planned: ${plannedShotDuration}s`);
          setRealVideoDuration(vid.duration);
          
          // Update the store so the timeline track width matches the real video duration!
          if (Math.abs(vid.duration - plannedShotDuration) > 0.1) {
              console.log(`[VideoView] Updating store duration for shot ${activeShotIndex} to ${vid.duration}`);
              updateShotDuration(activeShotIndex, vid.duration);
          }
      }
  };

  // Handle local seek (progress bar)
  const handleLocalSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
      const seekTime = parseFloat(e.target.value);
      setLocalTime(seekTime);
      
      if (videoRef.current) {
          videoRef.current.currentTime = seekTime;
      }
      
      // Update global time accordingly
      const currentShotStart = shotAssets?.slice(0, activeShotIndex).reduce((acc, s) => acc + (s.duration_s || 5), 0) || 0;
      setGlobalTime(currentShotStart + seekTime);
  };
  
  // Handle global timeline seek (click/drag on timeline)
  const timelineRef = useRef<HTMLDivElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  
  const handleTimelineInteraction = (e: React.MouseEvent<HTMLDivElement>) => {
      if (!trackRef.current || !shotAssets) return;
      
      const rect = trackRef.current.getBoundingClientRect();
      const labelWidth = 96; // w-24
      const clickX = e.clientX - rect.left - labelWidth;
      const trackWidth = rect.width - labelWidth;
      
      if (clickX < 0) return; // Clicked on label
      
      const percentage = Math.max(0, Math.min(1, clickX / trackWidth));
      const seekGlobalTime = percentage * totalDuration;
      
      setGlobalTime(seekGlobalTime);
      
      // Calculate which shot and local time
      let accumulated = 0;
      for (let i = 0; i < shotAssets.length; i++) {
          const duration = shotAssets[i].duration_s || 5;
          if (seekGlobalTime >= accumulated && seekGlobalTime < accumulated + duration) {
              setActiveShotIndex(i);
              const localSeek = seekGlobalTime - accumulated;
              setLocalTime(localSeek);
              
              if (videoRef.current) {
                  // If staying in same shot
                  if (i === activeShotIndex) {
                      // Check if video is ready enough to seek
                      if (videoRef.current.readyState >= 1) { // HAVE_METADATA
                          videoRef.current.currentTime = localSeek;
                      } else {
                          // Not ready yet, queue it
                          pendingSeekTimeRef.current = localSeek;
                      }
                  } else {
                      // Changing shot, component will remount, queue it
                      pendingSeekTimeRef.current = localSeek;
                  }
              }
              return;
          }
          accumulated += duration;
      }
      
      // If past end
      setActiveShotIndex(shotAssets.length - 1);
      if (videoRef.current) {
           const lastShotDuration = shotAssets[shotAssets.length - 1].duration_s || 5;
           if (videoRef.current.readyState >= 1) {
               videoRef.current.currentTime = lastShotDuration;
           } else {
               pendingSeekTimeRef.current = lastShotDuration;
           }
      }
  };

  const handleDragOver = (e: React.MouseEvent<HTMLDivElement>) => {
      // Only handle drag if mouse is down (buttons === 1)
      if (e.buttons === 1) {
          handleTimelineInteraction(e);
      }
  };

  const handlePlayheadDragStart = (e: React.MouseEvent<HTMLDivElement>) => {
      e.stopPropagation(); // Prevent triggering track click immediately
      e.preventDefault();
      setIsDragging(true);
      
      const handleMouseMove = (moveEvent: MouseEvent) => {
          if (!trackRef.current || !shotAssets) return;
          const rect = trackRef.current.getBoundingClientRect();
          const labelWidth = 96; 
          
          const clickX = moveEvent.clientX - rect.left - labelWidth;
          const trackWidth = rect.width - labelWidth;
          
          const percentage = Math.max(0, Math.min(1, clickX / trackWidth));
          const seekGlobalTime = percentage * totalDuration;
          
          // Direct DOM manipulation for zero-latency UI update
          if (playheadRef.current) {
              playheadRef.current.style.left = `calc(6rem + ${percentage * 100}% - ${percentage * 6}rem)`;
          }

          // Throttle state updates and video seeking
          const now = Date.now();
          if (now - lastSeekTimeRef.current < 50) { // ~20fps for state updates
              return;
          }
          lastSeekTimeRef.current = now;
          
          // Sync React state (will trigger re-render, but thanks to memo it should be fast)
          setGlobalTime(seekGlobalTime);

          // Reuse the seeking logic
          let accumulated = 0;
          for (let i = 0; i < shotAssets.length; i++) {
              const duration = shotAssets[i].duration_s || 5;
              if (seekGlobalTime >= accumulated && seekGlobalTime < accumulated + duration) {
                  setActiveShotIndex(i);
                  const localSeek = seekGlobalTime - accumulated;
                  setLocalTime(localSeek);
                  
                  if (videoRef.current) {
                      if (i === activeShotIndex) {
                          if (videoRef.current.readyState >= 1) {
                              videoRef.current.currentTime = localSeek;
                          } else {
                              pendingSeekTimeRef.current = localSeek;
                          }
                      } else {
                          pendingSeekTimeRef.current = localSeek;
                      }
                  }
                  return;
              }
              accumulated += duration;
          }
          
          setActiveShotIndex(shotAssets.length - 1);
          if (videoRef.current) {
              const lastShotDuration = shotAssets[shotAssets.length - 1].duration_s || 5;
              if (videoRef.current.readyState >= 1) {
                   videoRef.current.currentTime = lastShotDuration;
              } else {
                   pendingSeekTimeRef.current = lastShotDuration;
              }
          }
      };

      const handleMouseUp = () => {
          setIsDragging(false);
          document.removeEventListener('mousemove', handleMouseMove);
          document.removeEventListener('mouseup', handleMouseUp);
          
          // Final sync
          // We can't easily get the *exact* last seekGlobalTime here without recalculating
          // But since we setGlobalTime in the throttled loop, it might be slightly off.
          // However, for UX, the user stops dragging, and the last render will put the playhead 
          // where globalTime is. 
          // If we want perfection, we could trigger one last update here.
      };

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
  };

  const formatTime = (seconds: number) => {
      const mins = Math.floor(seconds / 60);
      const secs = Math.floor(seconds % 60);
      return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleVideoLoadedMetadata = (e: React.SyntheticEvent<HTMLVideoElement>) => {
      handleVideoDurationChange(e);
      // Apply pending seek if exists
      if (pendingSeekTimeRef.current !== null) {
          e.currentTarget.currentTime = pendingSeekTimeRef.current;
          pendingSeekTimeRef.current = null;
      }
  };

  return (
    <div className="flex h-full bg-zinc-900 text-white overflow-hidden">
      {/* Left Feedback Panel */}
      <div className="w-72 bg-zinc-800 border-r border-zinc-700 flex flex-col">
        {/* ... (Previous Left Panel Code) ... */}
        <div className="p-4 border-b border-zinc-700">
            <h2 className="font-semibold text-lg mb-1">健康科普视频</h2>
            <div className="flex gap-4 text-xs text-zinc-400">
                <span>720P</span>
                <span>30 FPS</span>
                <span>Generated</span>
            </div>
        </div>
        
        <div className="flex-1 p-4 overflow-y-auto">
            <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">微调建议</h3>
            <div className="space-y-3">
                <div className="bg-zinc-700/50 p-3 rounded-lg text-sm border border-zinc-600">
                   <p className="text-zinc-400 text-xs italic">暂无建议。请在下方输入框提交修改意见。</p>
                </div>
            </div>
        </div>

        <div className="p-4 border-t border-zinc-700 bg-zinc-800">
            <div className="relative">
                <input 
                    type="text" 
                    placeholder="输入修改意见..." 
                    className="w-full bg-zinc-900 border border-zinc-600 rounded-lg py-2 px-3 text-sm focus:outline-none focus:border-primary-500"
                />
                <button className="absolute right-2 top-2 text-primary-500 hover:text-primary-400">
                    <MessageSquare size={16} />
                </button>
            </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Video Player Area */}
        <div className="flex-1 flex flex-col relative bg-black">
            <div className="flex-1 flex items-center justify-center p-8">
                <div className="aspect-video w-full max-w-4xl bg-zinc-800 rounded-lg shadow-2xl overflow-hidden relative group">
                    {/* Video Content */}
                    <div className="absolute inset-0 flex items-center justify-center bg-zinc-900">
                        {isVideo ? (
                            <video 
                                ref={videoRef}
                                key={currentVideoUrl} 
                                src={currentVideoUrl} 
                                className={clsx("w-full h-full object-contain transition-all duration-75", isDragging && "blur-[2px] opacity-80 scale-[1.01]")} 
                                controls={false}
                                onEnded={handleVideoEnded}
                                onDurationChange={handleVideoDurationChange}
                                onLoadedMetadata={handleVideoLoadedMetadata}
                            />
                        ) : (
                            <div className="w-full h-full flex items-center justify-center bg-zinc-800 text-zinc-600">
                                <p>No Video Available</p>
                            </div>
                        )}
                        
                        {!isPlaying && (
                            <div className="absolute inset-0 flex items-center justify-center bg-black/20">
                                <button 
                                    onClick={() => setIsPlaying(true)}
                                    className="w-16 h-16 bg-white/10 backdrop-blur-sm rounded-full flex items-center justify-center hover:bg-white/20 transition-all transform hover:scale-105"
                                >
                                    <Play size={32} fill="white" className="ml-1" />
                                </button>
                            </div>
                        )}
                         {isPlaying && (
                             <div className="absolute bottom-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button 
                                    onClick={() => setIsPlaying(false)}
                                    className="w-10 h-10 bg-black/50 backdrop-blur-sm rounded-full flex items-center justify-center hover:bg-black/70"
                                >
                                    <Pause size={20} fill="white" />
                                </button>
                             </div>
                         )}
                    </div>
                </div>
            </div>
            
            {/* Player Controls */}
            <div className="h-16 bg-zinc-800 border-t border-zinc-700 flex flex-col justify-center px-6 gap-2">
                 {/* Local Shot Progress Bar */}
                 <div className="flex items-center gap-3 text-xs font-mono text-zinc-400">
                    <span>{formatTime(localTime)}</span>
                    <input 
                        type="range" 
                        min="0" 
                        max={realVideoDuration} 
                        step="0.05"
                        value={localTime} 
                        onChange={handleLocalSeek}
                        className="flex-1 h-1 bg-zinc-600 rounded-lg appearance-none cursor-pointer accent-primary-500 hover:accent-primary-400"
                    />
                    <span>{formatTime(realVideoDuration)}</span>
                 </div>
                 
                 <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <button className="text-zinc-400 hover:text-white" onClick={() => setActiveShotIndex(Math.max(0, activeShotIndex - 1))}><SkipBack size={20} /></button>
                        <button onClick={() => setIsPlaying(!isPlaying)} className="text-white hover:text-primary-400">
                            {isPlaying ? <Pause size={24} fill="currentColor" /> : <Play size={24} fill="currentColor" />}
                        </button>
                        <button className="text-zinc-400 hover:text-white" onClick={() => setActiveShotIndex(Math.min((shotAssets?.length || 1) - 1, activeShotIndex + 1))}><SkipForward size={20} /></button>
                        <div className="text-xs font-mono text-zinc-400 ml-2">Shot {activeShotIndex + 1} / {shotAssets?.length || 1}</div>
                    </div>
                    <div className="flex items-center gap-4">
                         <button className="text-zinc-400 hover:text-white"><Volume2 size={20} /></button>
                         <button className="text-zinc-400 hover:text-white"><Settings size={20} /></button>
                    </div>
                </div>
            </div>
        </div>

        {/* Timeline Area */}
        <div className="h-64 bg-zinc-900 border-t border-zinc-800 flex flex-col relative">
            <div className="flex-1 overflow-x-auto p-4 relative no-scrollbar">
                 {/* Tracks Container */}
                 <div 
                    className="space-y-2 mt-6 relative min-w-full"
                    ref={trackRef}
                    onMouseDown={handleTimelineInteraction}
                    onMouseMove={handleDragOver}
                 >
                    {/* Playhead Line - Positioned ABSOLUTELY to cover the tracks */}
                    <div 
                        ref={playheadRef}
                        className="absolute -top-4 -bottom-4 z-50 pointer-events-none transition-all duration-75 ease-linear"
                        style={{ left: `calc(6rem + ${(globalTime / totalDuration) * 100}% - ${(globalTime / totalDuration) * 6}rem)` }}
                    >
                         {/* Invisible Grab Area - Wider for easier clicking */}
                          <div 
                            className="absolute top-0 bottom-0 -left-2 w-4 cursor-ew-resize pointer-events-auto z-50 opacity-0 hover:opacity-10 group/playhead"
                            onMouseDown={handlePlayheadDragStart}
                          ></div>
                         
                         {/* Visible Line */}
                         <div className="absolute top-0 bottom-0 w-0.5 bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)] pointer-events-none"></div>
                         
                         {/* Diamond Handle */}
                         <div className="absolute -top-1 -left-[5px] w-3 h-3 bg-red-500 rotate-45 shadow-md border border-zinc-900 pointer-events-none"></div>
                    </div>

                    {/* Video Track */}
                    <div className="flex h-20 group relative select-none">
                        <div className="w-24 flex-shrink-0 flex items-center text-xs text-zinc-500 font-medium">Video</div>
                        <div className="flex-1 bg-zinc-800/50 rounded-lg overflow-hidden flex relative ring-1 ring-zinc-700/50">
                            {shotAssets ? (
                                shotAssets.map((shot, i) => (
                                    <div 
                                        key={shot.shot_id} 
                                        className={clsx(
                                            "border-r border-zinc-900/50 transition-colors relative overflow-hidden cursor-pointer group/shot",
                                            i === activeShotIndex ? "ring-2 ring-teal-500 z-10" : "hover:brightness-110"
                                        )}
                                        style={{ width: `${((shot.duration_s || 5) / totalDuration) * 100}%` }}
                                        onClick={() => {
                                            setActiveShotIndex(i);
                                            const startTime = shotAssets.slice(0, i).reduce((acc, s) => acc + (s.duration_s || 5), 0);
                                            setGlobalTime(startTime);
                                            if (videoRef.current) videoRef.current.currentTime = 0;
                                        }}
                                    >
                                        {/* Real Filmstrip visual effect */}
                                        <div className="absolute inset-0 flex opacity-60 group-hover/shot:opacity-100 transition-all bg-black">
                                            <VideoTrackItem 
                                                videoUrl={shot.video_url} 
                                                duration={shot.duration_s || 5} 
                                            />
                                        </div>
                                        <div className="absolute inset-0 bg-gradient-to-b from-transparent to-black/30 pointer-events-none"></div>
                                        <span className="absolute bottom-1 left-2 text-[10px] text-white/90 font-mono font-medium truncate w-full px-1 shadow-sm z-20 pointer-events-none">
                                            Shot {i + 1}
                                        </span>
                                        <div className="absolute top-0 bottom-0 left-0 w-px bg-white/20 pointer-events-none"></div>
                                        <div className="absolute top-0 bottom-0 right-0 w-px bg-white/20 pointer-events-none"></div>
                                    </div>
                                ))
                            ) : (
                                [1, 2, 3, 4].map((i) => (
                                    <div key={i} className="flex-1 border-r border-zinc-900/50 bg-teal-900/30 relative overflow-hidden">
                                         <span className="absolute bottom-1 left-2 text-[10px] text-teal-200/50">Shot {i}</span>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>

                    {/* Audio Track */}
                    <div className="flex h-20 group mt-1">
                        <div className="w-24 flex-shrink-0 flex items-center text-xs text-zinc-500 font-medium">Audio</div>
                        <div className="flex-1 bg-zinc-800/50 rounded-lg overflow-hidden flex relative ring-1 ring-zinc-700/50">
                             {shotAssets ? (
                                shotAssets.map((shot, i) => (
                                    <div 
                                        key={shot.shot_id} 
                                        className="border-r border-zinc-900/50 relative overflow-hidden h-full"
                                        style={{ width: `${((shot.duration_s || 5) / totalDuration) * 100}%` }}
                                    >
                                        <AudioTrackItem videoUrl={shot.video_url} />
                                    </div>
                                ))
                             ) : (
                                <div className="w-full h-full flex items-center justify-center text-xs text-zinc-600">No Audio Data</div>
                             )}
                        </div>
                    </div>
                 </div>
            </div>
        </div>
      </div>
    </div>
  );
};

const ImageIcon = ({ size }: { size: number }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
        <circle cx="9" cy="9" r="2" />
        <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" />
    </svg>
);

// Helper for clsx
function clsx(...args: any[]) {
    return args.filter(Boolean).join(' ');
}

