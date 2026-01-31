import React, { useEffect, useRef, useState } from 'react';
import { assetQueue } from '../utils/queue';

interface VideoTrackItemProps {
    videoUrl: string;
    duration: number;
    height?: number;
}

export const VideoTrackItem: React.FC<VideoTrackItemProps> = React.memo(({ videoUrl, duration, height = 80 }) => {
    const [thumbnails, setThumbnails] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    
    useEffect(() => {
        if (!videoUrl) return;
        
        let isMounted = true;
        
        const loadTask = async () => {
            if (!isMounted) return;
            setLoading(true);

            try {
                // Use addWithRetry to handle network flakes
                const thumbs = await assetQueue.addWithRetry(async () => {
                    if (!isMounted) throw new Error("Component unmounted");
                    // Use clean URL without timestamp to allow browser caching if possible, 
                    // relying on retry logic for robustness instead of cache-busting
                    return generateThumbnails(videoUrl, duration);
                });

                if (isMounted) {
                    setThumbnails(thumbs);
                    setLoading(false);
                }
            } catch (err) {
                // Ignore unmounted errors
                if (err instanceof Error && err.message === "Component unmounted") return;
                
                // Silently handle abort errors which are common during quick navigation
                if (err instanceof Error && (err.name === 'AbortError' || err.message.includes('Aborted'))) return;

                console.error("Failed to load thumbnails:", videoUrl, err);
                if (isMounted) setLoading(false);
            }
        };

        loadTask();
        
        return () => {
            isMounted = false;
        };
    }, [videoUrl, duration]);

    if (loading && thumbnails.length === 0) {
         // Show solid color blocks while loading
         return (
             <div className="w-full h-full flex">
                 {Array.from({ length: 8 }).map((_, i) => (
                     <div key={i} className="flex-1 bg-zinc-800 border-r border-zinc-700 animate-pulse"></div>
                 ))}
             </div>
         );
    }

    return (
        <div className="w-full h-full flex overflow-hidden">
            {thumbnails.map((src, i) => (
                <div key={i} className="flex-1 h-full relative border-r border-white/10 last:border-0">
                    <img src={src} className="w-full h-full object-cover" alt={`frame-${i}`} />
                </div>
            ))}
        </div>
    );
});

// 独立的缩略图生成函数，不依赖 React 组件状态，纯净且易于被队列调用
async function generateThumbnails(videoUrl: string, duration: number): Promise<string[]> {
    return new Promise((resolve, reject) => {
        const video = document.createElement('video');
        video.crossOrigin = "anonymous";
        video.src = videoUrl;
        video.muted = true;
        video.preload = "auto";
        
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        const thumbs: string[] = [];
        const count = 8; 
        const interval = duration / count;
        let currentTime = 0;
        
        // Timeout protection
        const timeoutId = setTimeout(() => {
            video.removeAttribute('src');
            video.load();
            reject(new Error("Thumbnail generation timed out"));
        }, 15000); // 15s timeout

        const cleanup = () => {
            clearTimeout(timeoutId);
            video.removeAttribute('src');
            video.load();
        };

        const captureFrame = async () => {
            if (currentTime > duration || thumbs.length >= count) {
                cleanup();
                resolve(thumbs);
                return;
            }
            video.currentTime = currentTime;
        };
        
        video.onloadeddata = () => {
                canvas.width = video.videoWidth / 4; 
                canvas.height = video.videoHeight / 4;
                captureFrame();
        };
        
        video.onseeked = () => {
            if (context) {
                context.drawImage(video, 0, 0, canvas.width, canvas.height);
                thumbs.push(canvas.toDataURL('image/jpeg', 0.5));
            }
            currentTime += interval;
            captureFrame();
        };
        
        video.onerror = (e) => {
            cleanup();
            reject(e);
        };
        
        video.load();
    });
}

interface AudioTrackItemProps {
    videoUrl: string;
}

export const AudioTrackItem: React.FC<AudioTrackItemProps> = React.memo(({ videoUrl }) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [error, setError] = useState(false);

    useEffect(() => {
        if (!videoUrl) return;

        let isMounted = true;

        const loadTask = async () => {
             try {
                // Use addWithRetry
                const audioBuffer = await assetQueue.addWithRetry(async () => {
                    if (!isMounted) throw new Error("Component unmounted");
                    // Use clean URL
                    return fetchAudioData(videoUrl);
                });
                
                if (isMounted && audioBuffer) {
                    drawWaveform(audioBuffer, canvasRef.current);
                }
             } catch (err) {
                 if (err instanceof Error && err.message === "Component unmounted") return;
                 // Silently handle abort errors
                 if (err instanceof Error && (err.name === 'AbortError' || err.message.includes('Aborted'))) return;
                 
                 console.error("Audio waveform generation failed:", videoUrl, err);
                 if (isMounted) setError(true);
             }
        };

        loadTask();

        return () => {
            isMounted = false;
        };
    }, [videoUrl]);

    const drawWaveform = (buffer: AudioBuffer, canvas: HTMLCanvasElement | null) => {
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const width = canvas.width;
        const height = canvas.height;
        const data = buffer.getChannelData(0); // Left channel
        const step = Math.ceil(data.length / width);
        const amp = height / 2;

        ctx.clearRect(0, 0, width, height);
        ctx.fillStyle = '#10b981'; // emerald-500
        
        ctx.beginPath();
        for (let i = 0; i < width; i++) {
            let min = 1.0;
            let max = -1.0;
            for (let j = 0; j < step; j++) {
                const datum = data[i * step + j];
                if (datum < min) min = datum;
                if (datum > max) max = datum;
            }
            if (!isFinite(min)) min = 0;
            if (!isFinite(max)) max = 0;

            const x = i;
            const h = Math.max(1, (max - min) * amp);
            ctx.fillRect(x, (height - h) / 2, 1, h);
        }
    };

    if (error) {
        return (
            <div className="w-full h-full bg-red-900/20 flex items-center justify-center text-[10px] text-red-400">
                No Audio
            </div>
        );
    }

    return (
        <canvas 
            ref={canvasRef} 
            width={300} 
            height={50} 
            className="w-full h-full"
        />
    );
});

// 独立的音频获取函数
async function fetchAudioData(videoUrl: string): Promise<AudioBuffer> {
    const response = await fetch(videoUrl);
    if (!response.ok) throw new Error('Fetch failed');
    const arrayBuffer = await response.arrayBuffer();
    
    // Create context only when needed and close it immediately
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    const audioContext = new AudioContextClass();
    
    try {
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        return audioBuffer;
    } finally {
        if (audioContext.state !== 'closed') {
            audioContext.close().catch(console.error);
        }
    }
}
