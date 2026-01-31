import axios from 'axios';

// API Client configuration
const apiClient = axios.create({
  baseURL: '/api/v1/t2v', // Use proxy
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface GenerationRequest {
  user_prompt: string;
  quality_mode?: 'fast' | 'balanced' | 'high';
  resolution?: '1280x720' | '1920x1080';
  duration_preference_s?: number;
}

export interface GenerationResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface ShotAsset {
  shot_id: number;
  video_url: string;
  audio_url: string;
  duration_s: number;
}

export interface JobStatusResponse {
  job_id: string;
  status: 'CREATED' | 'SUBMITTED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED';
  script?: string;
  shot_plan?: {
    shots: Array<{
      shot_id: number;
      visual_prompt: string;
      narration: string;
      duration: number;
      // Add other fields if necessary
    }>
  };
  assets?: Array<any>; // Backend returns 'assets'
  error?: any; // Backend returns 'error'
  
  // Legacy fields to maintain compatibility if needed, but better to remove
  // shot_assets?: ShotAsset[]; 
  // error_details?: any;
}

export interface ReviseRequest {
    feedback: string;
}

export interface ReviseResponse {
    job_id: string;
    parent_job_id: string;
    status: string;
    targeted_fields: string[];
}


export const api = {
  // Submit generation job
  generateVideo: async (params: GenerationRequest): Promise<GenerationResponse> => {
    const response = await apiClient.post<GenerationResponse>('/generate', params);
    return response.data;
  },

  // Get job status
  getJobStatus: async (jobId: string): Promise<JobStatusResponse> => {
    const response = await apiClient.get<JobStatusResponse>(`/jobs/${jobId}`);
    return response.data;
  },

  // Revise job
  reviseVideo: async (jobId: string, feedback: string): Promise<ReviseResponse> => {
      const response = await apiClient.post<ReviseResponse>(`/jobs/${jobId}/revise`, { feedback });
      return response.data;
  }
};
