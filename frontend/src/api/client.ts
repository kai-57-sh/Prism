import axios from 'axios';

const assetsBase = new URL('./', import.meta.url);
const appBase = new URL('../', assetsBase);

// API Client configuration
// Derive the app base from the bundled asset URL so requests stay under the studio prefix.
const apiClient = axios.create({
  baseURL: new URL('api/v1/t2v', appBase).toString(),
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

export interface ShotPlanShot {
  shot_id: number;
  visual_prompt: string;
  narration: string;
  duration: number;
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

export interface ShotPlanUpdateRequest {
  visual_prompt?: string;
  narration?: string;
}

export interface ShotRegenerateResponse {
  shot_id: number;
  asset?: ShotAsset;
  message: string;
}


export const api = {
  // Submit planning job (script + shot plan only)
  planVideo: async (params: GenerationRequest): Promise<GenerationResponse> => {
    const response = await apiClient.post<GenerationResponse>('/plan', params);
    return response.data;
  },

  // Submit generation job
  generateVideo: async (params: GenerationRequest): Promise<GenerationResponse> => {
    const response = await apiClient.post<GenerationResponse>('/generate', params);
    return response.data;
  },

  // Trigger render for existing job
  renderVideo: async (jobId: string): Promise<GenerationResponse> => {
    const response = await apiClient.post<GenerationResponse>(`/jobs/${jobId}/render`);
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
  },

  // Update a single shot in the shot plan
  updateShotPlan: async (
    jobId: string,
    shotId: number,
    payload: ShotPlanUpdateRequest
  ): Promise<ShotPlanShot> => {
    const response = await apiClient.patch<ShotPlanShot>(`/jobs/${jobId}/shots/${shotId}`, payload);
    return response.data;
  },

  // Regenerate a single shot
  regenerateShot: async (
    jobId: string,
    shotId: number,
    payload?: ShotPlanUpdateRequest
  ): Promise<ShotRegenerateResponse> => {
    const response = await apiClient.post<ShotRegenerateResponse>(`/jobs/${jobId}/shots/${shotId}/regenerate`, payload || {});
    return response.data;
  },
};
