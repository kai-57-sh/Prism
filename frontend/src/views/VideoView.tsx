import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, SkipBack, SkipForward, Volume2, Download, Loader2 } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import { api } from '../api/client';
import { VideoTrackItem, AudioTrackItem } from '../components/TimelineTracks';

export const VideoView = () => {
  const {
    appState,
    setAppState,
    addMessage,
    shotAssets,
    updateShotDuration,
    shotPlan,
    currentJobId,
    setShotAssets,
    updateShotPlanShot,
  } = useAppStore();
  const [isPlaying, setIsPlaying] = useState(false);
  const [activeShotIndex, setActiveShotIndex] = useState(0);
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const secondaryVideoRef = useRef<HTMLVideoElement>(null);
  const pendingSeekTimeRef = useRef<number | null>(null);
  const [volume, setVolume] = useState(0.8);
  const [isVolumeOpen, setIsVolumeOpen] = useState(false);
  const [isDownloadOpen, setIsDownloadOpen] = useState(false);
  const [downloadBusy, setDownloadBusy] = useState({ video: false, audio: false, all: false });
  const volumeWrapRef = useRef<HTMLDivElement>(null);
  const downloadWrapRef = useRef<HTMLDivElement>(null);
  const [shotEdits, setShotEdits] = useState<Record<number, { visual: string; narration: string }>>({});
  const [comparisonByShot, setComparisonByShot] = useState<Record<number, { previous: any; current: any }>>({});
  const [comparisonShotId, setComparisonShotId] = useState<number | null>(null);
  const [comparisonView, setComparisonView] = useState<'current' | 'previous'>('current');
  const [regeneratingShotId, setRegeneratingShotId] = useState<number | null>(null);
  const [savingShots, setSavingShots] = useState<Record<number, boolean>>({});
  const shotCount = shotPlan?.length ?? 0;
  const isRendering = appState === 'RENDERING';

  const baseActiveAsset = shotAssets && shotAssets.length > 0 ? shotAssets[activeShotIndex] : undefined;
  const activeShotId = baseActiveAsset?.shot_id ?? activeShotIndex + 1;
  const comparisonEntry = comparisonShotId !== null ? comparisonByShot[comparisonShotId] : undefined;
  const isComparing = Boolean(
    comparisonEntry &&
    comparisonShotId === activeShotId &&
    comparisonEntry.previous &&
    comparisonEntry.current
  );
  const currentAsset = isComparing ? comparisonEntry?.current : baseActiveAsset;
  const previousAsset = isComparing ? comparisonEntry?.previous : undefined;
  const activeAsset = isComparing
    ? (comparisonView === 'current' ? currentAsset : previousAsset)
    : baseActiveAsset;

  // Use the first generated video if available, or fallback to mock
  const currentVideoUrl = activeAsset?.video_url || "";
  const currentAudioUrl = activeAsset?.audio_url || "";
  const isVideo = Boolean(currentVideoUrl);

  const normalizeAssetUrl = (url: string) => {
      if (!url) return "";
      try {
          const parsed = new URL(url, window.location.origin);
          if (parsed.pathname.startsWith("/static/") && parsed.origin !== window.location.origin) {
              return `${parsed.pathname}${parsed.search}${parsed.hash}`;
          }
          return parsed.toString();
      } catch {
          return url;
      }
  };

  const resolveDownloadName = (url: string, fallback: string) => {
      try {
          const resolved = new URL(url, window.location.origin);
          const parts = resolved.pathname.split("/").filter(Boolean);
          return parts[parts.length - 1] || fallback;
      } catch {
          return fallback;
      }
  };

  const downloadFile = async (url: string, fallbackName: string) => {
      const resolvedUrl = normalizeAssetUrl(url);
      const cacheBustedUrl = resolvedUrl
          ? `${resolvedUrl}${resolvedUrl.includes("?") ? "&" : "?"}t=${Date.now()}`
          : resolvedUrl;
      const response = await fetch(cacheBustedUrl, { mode: "cors", cache: "no-store" });
      if (!response.ok) {
          throw new Error(`Download failed: ${response.status}`);
      }
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = resolveDownloadName(cacheBustedUrl, fallbackName);
      link.style.display = "none";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);
  };

  const downloadAsset = async (url: string, kind: "video" | "audio") => {
      if (!url || downloadBusy[kind] || downloadBusy.all) return;
      setDownloadBusy((prev) => ({ ...prev, [kind]: true }));
      try {
          await downloadFile(url, kind === "video" ? "video.mp4" : "audio.mp3");
          setIsDownloadOpen(false);
      } catch (error) {
          console.error("Download error:", error);
          addMessage(
              "ai",
              kind === "video"
                  ? "视频下载失败，可能是静态资源跨域或文件不存在。"
                  : "音频下载失败，可能是静态资源跨域或文件不存在。"
          );
      } finally {
          setDownloadBusy((prev) => ({ ...prev, [kind]: false }));
      }
  };

  const collectAllDownloadItems = () => {
      const assets = shotAssets && shotAssets.length > 0 ? shotAssets : (activeAsset ? [activeAsset] : []);
      const items: Array<{ url: string; fallback: string }> = [];
      assets.forEach((asset, index) => {
          const shotLabel = asset?.shot_id ? `shot_${asset.shot_id}` : `shot_${index + 1}`;
          if (asset?.video_url) {
              items.push({ url: asset.video_url, fallback: `${shotLabel}_video.mp4` });
          }
          if (asset?.audio_url) {
              items.push({ url: asset.audio_url, fallback: `${shotLabel}_audio.mp3` });
          }
      });
      return items;
  };

  const downloadAllAssets = async () => {
      if (downloadBusy.all) return;
      const items = collectAllDownloadItems();
      if (items.length === 0) return;
      setDownloadBusy((prev) => ({ ...prev, all: true }));
      let successCount = 0;
      let failureCount = 0;
      for (const item of items) {
          try {
              await downloadFile(item.url, item.fallback);
              successCount += 1;
          } catch (error) {
              console.error("Batch download error:", error);
              failureCount += 1;
          }
      }
      setIsDownloadOpen(false);
      if (failureCount > 0) {
          addMessage(
              "ai",
              successCount === 0
                  ? "音视频批量下载失败，可能是静态资源跨域或文件不存在。"
                  : `部分下载失败（成功 ${successCount} 个，失败 ${failureCount} 个）。`
          );
      }
      setDownloadBusy((prev) => ({ ...prev, all: false }));
  };

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
      if (audioRef.current) {
          audioRef.current.pause();
          audioRef.current.currentTime = 0;
      }
  };

  const totalDuration = shotAssets ? shotAssets.reduce((acc, shot) => acc + (shot.duration_s || 5), 0) : 20;
  // Get duration of current active shot from metadata (fallback)
  const plannedShotDuration = activeAsset ? (activeAsset.duration_s || 5) : 5;
  
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

  useEffect(() => {
    if (audioRef.current) {
        audioRef.current.currentTime = 0;
          if (isPlaying && currentAudioUrl) {
              audioRef.current.play().catch(e => console.error("Audio play error:", e));
          }
      }
  }, [activeShotIndex, currentAudioUrl, isPlaying]);

  useEffect(() => {
    if (appState !== 'RENDERING' || !currentJobId) return;
    const interval = window.setInterval(async () => {
        try {
            const status = await api.getJobStatus(currentJobId);
            if (status.assets && status.assets.length > 0) {
                setShotAssets(status.assets);
            }
            if (status.status === 'SUCCEEDED') {
                if (status.assets) setShotAssets(status.assets);
                setAppState('COMPLETED');
                clearInterval(interval);
            } else if (status.status === 'FAILED') {
                setAppState('EDITING');
                addMessage('ai', `生成失败: ${status.error?.message || '未知错误'}`);
                clearInterval(interval);
            }
        } catch (e) {
            console.error('Render polling error', e);
        }
    }, 2000);

    return () => {
        clearInterval(interval);
    };
  }, [appState, currentJobId, setAppState, setShotAssets, addMessage]);

  useEffect(() => {
      if (!isComparing || !videoRef.current) return;
      if (videoRef.current.readyState >= 1) {
          videoRef.current.currentTime = localTime;
      } else {
          pendingSeekTimeRef.current = localTime;
      }
      if (audioRef.current && currentAudioUrl) {
          audioRef.current.currentTime = localTime;
      }
  }, [comparisonView, isComparing, currentVideoUrl, currentAudioUrl]);

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

               if (audioRef.current && currentAudioUrl) {
                   const audioDelta = Math.abs(audioRef.current.currentTime - currentTime);
                   if (audioDelta > 0.1) {
                       audioRef.current.currentTime = currentTime;
                   }
               }
               
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
  }, [isPlaying, activeShotIndex, shotAssets, totalDuration, currentAudioUrl]);

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
    if (audioRef.current) {
        if (!currentAudioUrl) {
            audioRef.current.pause();
        } else if (isPlaying) {
            audioRef.current.play().catch(e => console.error("Audio play error:", e));
        } else {
            audioRef.current.pause();
        }
    }
  }, [isPlaying, currentVideoUrl, currentAudioUrl]); // React to play state change and source changes

  useEffect(() => {
    if (videoRef.current) {
        videoRef.current.volume = volume;
    }
    if (audioRef.current) {
        audioRef.current.volume = volume;
    }
  }, [volume, currentVideoUrl, currentAudioUrl]);

  useEffect(() => {
    if (!isComparing || !secondaryVideoRef.current) return;
    if (!isPlaying) {
        if (secondaryVideoRef.current.readyState >= 1) {
            secondaryVideoRef.current.currentTime = localTime;
        }
        return;
    }
    const delta = Math.abs(secondaryVideoRef.current.currentTime - localTime);
    if (delta > 0.15) {
        secondaryVideoRef.current.currentTime = localTime;
    }
  }, [localTime, isComparing, isPlaying, comparisonView, currentAsset?.video_url, previousAsset?.video_url]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
        const target = event.target as Node;
        if (volumeWrapRef.current && !volumeWrapRef.current.contains(target)) {
            setIsVolumeOpen(false);
        }
        if (downloadWrapRef.current && !downloadWrapRef.current.contains(target)) {
            setIsDownloadOpen(false);
        }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (!shotPlan || shotPlan.length === 0) return;
    setShotEdits((prev) => {
        const next = { ...prev };
        shotPlan.forEach((shot) => {
            if (!next[shot.shot_id]) {
                next[shot.shot_id] = {
                    visual: shot.visual_prompt || '',
                    narration: shot.narration || '',
                };
            }
        });
        return next;
    });
  }, [shotPlan]);

  useEffect(() => {
    const textareas = document.querySelectorAll<HTMLTextAreaElement>('[data-autoresize="true"]');
    textareas.forEach((el) => {
        const maxHeight = Number(el.dataset.maxheight || '160');
        el.style.height = 'auto';
        const nextHeight = Math.min(el.scrollHeight, maxHeight);
        el.style.height = `${nextHeight}px`;
        el.style.overflowY = el.scrollHeight > maxHeight ? 'auto' : 'hidden';
    });
  }, [shotEdits, shotPlan]);

  useEffect(() => {
    if (!shotAssets || shotAssets.length === 0) return;
    setComparisonByShot((prev) => {
        let changed = false;
        const next = { ...prev };
        Object.keys(prev).forEach((key) => {
            const shotId = Number(key);
            const asset = shotAssets.find((item) => item.shot_id === shotId);
            if (!asset) return;
            const existing = prev[shotId];
            if (!existing) return;
            if (existing.current?.video_url !== asset.video_url || existing.current?.audio_url !== asset.audio_url) {
                next[shotId] = { previous: existing.previous, current: asset };
                changed = true;
            }
        });
        return changed ? next : prev;
    });
  }, [shotAssets]);

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

  const persistShotEdits = async (shotId: number) => {
    if (!currentJobId) return;
    const edits = shotEdits[shotId];
    if (!edits) return;

    setSavingShots((prev) => ({ ...prev, [shotId]: true }));
    try {
        await api.updateShotPlan(currentJobId, shotId, {
            visual_prompt: edits.visual,
            narration: edits.narration,
        });
        updateShotPlanShot(shotId, {
            visual_prompt: edits.visual,
            narration: edits.narration,
        });
    } catch (e) {
        console.error('Shot plan update failed', e);
    } finally {
        setSavingShots((prev) => ({ ...prev, [shotId]: false }));
    }
  };

  const handleRegenerateShot = async (shotId: number) => {
    if (isRendering) return;
    if (!currentJobId || !shotAssets || shotAssets.length === 0) return;
    const index = shotAssets.findIndex((asset) => asset.shot_id === shotId);
    if (index === -1) return;

    const edits = shotEdits[shotId];
    setRegeneratingShotId(shotId);
    try {
        const res = await api.regenerateShot(currentJobId, shotId, {
            visual_prompt: edits?.visual,
            narration: edits?.narration,
        });
        if (res.asset) {
            const previousAsset = shotAssets[index];
            setComparisonByShot((prev) => ({
                ...prev,
                [shotId]: {
                    previous: prev[shotId]?.current || previousAsset,
                    current: res.asset,
                },
            }));
            const nextAssets = [...shotAssets];
            nextAssets[index] = res.asset;
            setShotAssets(nextAssets);
            setComparisonShotId(shotId);
            setComparisonView('current');
            setActiveShotIndex(index);
        }
    } catch (e) {
        console.error('Shot regeneration failed', e);
    } finally {
        setRegeneratingShotId(null);
    }
  };

  const handleScriptEdit = (shotId: number, field: 'visual' | 'narration', value: string) => {
    setShotEdits((prev) => ({
        ...prev,
        [shotId]: {
            visual: field === 'visual' ? value : (prev[shotId]?.visual ?? ''),
            narration: field === 'narration' ? value : (prev[shotId]?.narration ?? ''),
        },
    }));
    updateShotPlanShot(shotId, field === 'visual' ? { visual_prompt: value } : { narration: value });
  };

  const handleTextareaChange = (
    shotId: number,
    field: 'visual' | 'narration',
    event: React.ChangeEvent<HTMLTextAreaElement>,
  ) => {
    handleScriptEdit(shotId, field, event.target.value);
    const maxHeight = Number(event.target.dataset.maxheight || '160');
    event.target.style.height = 'auto';
    const nextHeight = Math.min(event.target.scrollHeight, maxHeight);
    event.target.style.height = `${nextHeight}px`;
    event.target.style.overflowY = event.target.scrollHeight > maxHeight ? 'auto' : 'hidden';
  };

  // Handle local seek (progress bar)
  const handleLocalSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
      const seekTime = parseFloat(e.target.value);
      setLocalTime(seekTime);
      
      if (videoRef.current) {
          videoRef.current.currentTime = seekTime;
      }
      if (audioRef.current && currentAudioUrl) {
          audioRef.current.currentTime = seekTime;
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
              if (audioRef.current && currentAudioUrl) {
                  audioRef.current.currentTime = localSeek;
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
      if (audioRef.current && currentAudioUrl) {
           audioRef.current.currentTime = shotAssets[shotAssets.length - 1].duration_s || 5;
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
          if (audioRef.current && currentAudioUrl) {
              audioRef.current.currentTime = pendingSeekTimeRef.current;
          }
          pendingSeekTimeRef.current = null;
      }
  };

  return (
    <div className="flex h-full bg-zinc-900 text-white overflow-hidden">
      {/* Left Storyboard Panel */}
      <div className="w-72 bg-zinc-800 border-r border-zinc-700 flex flex-col">
        <div className="flex-1 p-4 overflow-y-auto no-scrollbar">
            <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">分镜脚本</h3>
            <div className={clsx(
                "grid gap-3",
                shotCount > 0 && shotCount <= 3 ? "grid-rows-[repeat(3,minmax(0,1fr))] h-full" : ""
            )}>
                {shotPlan && shotPlan.length > 0 ? (
                    shotPlan.map((shot) => {
                        const edits = shotEdits[shot.shot_id] || { visual: '', narration: '' };
                        const isGenerating = isRendering || regeneratingShotId === shot.shot_id;
                        return (
                            <div
                                key={shot.shot_id}
                                className="bg-zinc-700/40 p-3 rounded-lg text-sm border border-zinc-600 flex flex-col h-full"
                                onClick={() => {
                                    const index = shotAssets?.findIndex((asset) => asset.shot_id === shot.shot_id) ?? -1;
                                    if (index >= 0) setActiveShotIndex(index);
                                }}
                            >
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs font-semibold text-zinc-200">镜头 {shot.shot_id}</span>
                                        {savingShots[shot.shot_id] && (
                                            <span className="text-[10px] text-zinc-400">保存中...</span>
                                        )}
                                    </div>
                                    <button
                                        className={clsx(
                                            "text-xs px-2 py-1 rounded-md border transition-colors flex items-center gap-1",
                                            isGenerating
                                                ? "bg-green-100 text-green-700 border-green-200"
                                                : "bg-green-50 text-green-700 border-green-200 hover:bg-green-100"
                                        )}
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleRegenerateShot(shot.shot_id);
                                        }}
                                        disabled={isGenerating}
                                    >
                                        {isGenerating ? (
                                            <>
                                                <Loader2 size={12} className="animate-spin" /> 生成中
                                            </>
                                        ) : (
                                            "重新生成"
                                        )}
                                    </button>
                                </div>
                                <div className="space-y-2 flex-1 overflow-hidden">
                                    <div>
                                        <div className="text-[11px] text-zinc-400 mb-1">画面</div>
                                        <textarea
                                            rows={1}
                                            value={edits.visual}
                                            onChange={(e) => handleTextareaChange(shot.shot_id, 'visual', e)}
                                            onBlur={() => persistShotEdits(shot.shot_id)}
                                            data-autoresize="true"
                                            data-maxheight="140"
                                            className="w-full resize-none rounded-md bg-zinc-900/70 border border-zinc-600 px-2 py-1 text-xs text-zinc-100 focus:outline-none focus:border-primary-500 min-h-[72px] no-scrollbar"
                                        />
                                    </div>
                                    <div>
                                        <div className="text-[11px] text-zinc-400 mb-1">旁白</div>
                                        <textarea
                                            rows={1}
                                            value={edits.narration}
                                            onChange={(e) => handleTextareaChange(shot.shot_id, 'narration', e)}
                                            onBlur={() => persistShotEdits(shot.shot_id)}
                                            data-autoresize="true"
                                            data-maxheight="96"
                                            className="w-full resize-none rounded-md bg-zinc-900/70 border border-zinc-600 px-2 py-1 text-xs text-zinc-100 focus:outline-none focus:border-primary-500 min-h-[56px] no-scrollbar"
                                        />
                                    </div>
                                </div>
                            </div>
                        );
                    })
                ) : (
                    <div className="bg-zinc-700/40 p-3 rounded-lg text-xs text-zinc-400 border border-zinc-600">
                        暂无分镜脚本。
                    </div>
                )}
            </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Video Player Area */}
        <div className="flex-1 flex flex-col relative bg-black">
            <div className="flex-1 flex items-center justify-center p-4">
                <div className="w-full h-full bg-zinc-800 rounded-lg shadow-2xl overflow-hidden relative group">
                    {/* Video Content */}
                    <div className="absolute inset-0 flex items-center justify-center bg-zinc-900">
                        {isVideo ? (
                            isComparing && currentAsset?.video_url && previousAsset?.video_url ? (
                                <div
                                    className="relative w-full h-full cursor-pointer"
                                    onClick={(e) => {
                                        const target = e.target as HTMLElement;
                                        if (target.closest('button')) return;
                                        setComparisonView((prev) => (prev === 'current' ? 'previous' : 'current'));
                                    }}
                                >
                                    <video
                                        ref={comparisonView === 'current' ? videoRef : secondaryVideoRef}
                                        key={currentAsset.video_url}
                                        src={currentAsset.video_url}
                                        className={clsx(
                                            "absolute inset-0 w-full h-full object-contain transition-all duration-150",
                                            comparisonView === 'current' ? "opacity-100" : "opacity-0",
                                            comparisonView === 'current' && isDragging && "blur-[2px] opacity-80 scale-[1.01]"
                                        )}
                                        controls={false}
                                        muted={comparisonView !== 'current'}
                                        onEnded={comparisonView === 'current' ? handleVideoEnded : undefined}
                                        onDurationChange={comparisonView === 'current' ? handleVideoDurationChange : undefined}
                                        onLoadedMetadata={comparisonView === 'current' ? handleVideoLoadedMetadata : undefined}
                                    />
                                    <video
                                        ref={comparisonView === 'current' ? secondaryVideoRef : videoRef}
                                        key={previousAsset.video_url}
                                        src={previousAsset.video_url}
                                        className={clsx(
                                            "absolute inset-0 w-full h-full object-contain transition-all duration-150",
                                            comparisonView === 'current' ? "opacity-0" : "opacity-100",
                                            comparisonView !== 'current' && isDragging && "blur-[2px] opacity-80 scale-[1.01]"
                                        )}
                                        controls={false}
                                        muted={comparisonView === 'current'}
                                        onEnded={comparisonView === 'current' ? undefined : handleVideoEnded}
                                        onDurationChange={comparisonView === 'current' ? undefined : handleVideoDurationChange}
                                        onLoadedMetadata={comparisonView === 'current' ? undefined : handleVideoLoadedMetadata}
                                    />
                                    <span className="absolute top-3 left-3 text-[11px] px-2 py-0.5 rounded-full bg-black/50 text-white border border-white/10">
                                        {comparisonView === 'current' ? '当前版本' : '上一版'}
                                    </span>
                                    <span className="absolute bottom-3 left-1/2 -translate-x-1/2 text-[11px] px-2 py-0.5 rounded-full bg-white/10 text-white border border-white/10">
                                        点击切换版本
                                    </span>
                                </div>
                            ) : (
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
                            )
                        ) : (
                            <div className="w-full h-full flex items-center justify-center bg-zinc-800 text-zinc-600">
                                <p>No Video Available</p>
                            </div>
                        )}

                        {/* Hidden audio element for separate audio track playback */}
                        <audio
                            ref={audioRef}
                            src={currentAudioUrl || undefined}
                            preload="auto"
                            className="hidden"
                        />
                        
                        {!isPlaying && (
                            <div className="absolute inset-0 z-10 flex items-center justify-center bg-black/20">
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
                         <div className="relative" ref={volumeWrapRef}>
                            <button
                                className="text-zinc-400 hover:text-white"
                                onClick={() => {
                                    setIsVolumeOpen((prev) => !prev);
                                    setIsDownloadOpen(false);
                                }}
                                aria-label="Volume"
                            >
                                <Volume2 size={20} />
                            </button>
                            {isVolumeOpen && (
                                <div className="absolute right-0 bottom-8 bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 shadow-lg">
                                    <div className="flex items-center gap-2 text-xs text-zinc-300">
                                        <span>音量</span>
                                        <input
                                            type="range"
                                            min="0"
                                            max="100"
                                            value={Math.round(volume * 100)}
                                            onChange={(e) => setVolume(Math.max(0, Math.min(1, Number(e.target.value) / 100)))}
                                            className="w-28 h-1 bg-zinc-700 rounded-lg appearance-none cursor-pointer accent-primary-500"
                                        />
                                        <span className="w-8 text-right">{Math.round(volume * 100)}%</span>
                                    </div>
                                </div>
                            )}
                         </div>
                         <div className="relative z-20" ref={downloadWrapRef}>
                            <button
                                className="text-zinc-400 hover:text-white"
                                onClick={() => {
                                    setIsDownloadOpen((prev) => !prev);
                                    setIsVolumeOpen(false);
                                }}
                                aria-label="Download"
                            >
                                <Download size={20} />
                            </button>
                            {isDownloadOpen && (
                                <div className="absolute right-0 bottom-8 z-50 bg-zinc-900 border border-zinc-700 rounded-lg p-2 shadow-lg min-w-[140px]">
                                    <button
                                        type="button"
                                        className={`block w-full text-left px-3 py-2 rounded text-xs transition-colors ${
                                            !downloadBusy.all && (currentVideoUrl || currentAudioUrl)
                                                ? "text-zinc-200 hover:bg-zinc-800"
                                                : "text-zinc-500 cursor-not-allowed"
                                        }`}
                                        disabled={downloadBusy.all || (!currentVideoUrl && !currentAudioUrl)}
                                        onClick={downloadAllAssets}
                                    >
                                        {downloadBusy.all ? "下载中..." : "下载全部音视频"}
                                    </button>
                                    <button
                                        type="button"
                                        className={`block w-full text-left px-3 py-2 rounded text-xs transition-colors ${
                                            currentVideoUrl && !downloadBusy.video
                                                ? "text-zinc-200 hover:bg-zinc-800"
                                                : "text-zinc-500 cursor-not-allowed"
                                        }`}
                                        disabled={!currentVideoUrl || downloadBusy.video}
                                        onClick={() => downloadAsset(currentVideoUrl, "video")}
                                    >
                                        {downloadBusy.video ? "下载中..." : "下载视频"}
                                    </button>
                                    <button
                                        type="button"
                                        className={`block w-full text-left px-3 py-2 rounded text-xs transition-colors ${
                                            currentAudioUrl && !downloadBusy.audio
                                                ? "text-zinc-200 hover:bg-zinc-800"
                                                : "text-zinc-500 cursor-not-allowed"
                                        }`}
                                        disabled={!currentAudioUrl || downloadBusy.audio}
                                        onClick={() => downloadAsset(currentAudioUrl, "audio")}
                                    >
                                        {downloadBusy.audio ? "下载中..." : "下载音频"}
                                    </button>
                                </div>
                            )}
                         </div>
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
                                        <AudioTrackItem audioUrl={shot.audio_url} />
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
