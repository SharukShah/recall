export interface LociCreateRequest {
  items: string[];
  title: string;
  palace_theme?: string;
}

export interface LociLocation {
  position: number;
  location_name: string;
  item: string;
  vivid_image: string;
  narration: string;
}

export interface LociWalkthrough {
  palace_theme: string;
  introduction: string;
  locations: LociLocation[];
  conclusion: string;
}

export interface LociCreateResponse {
  session_id: string;
  title: string;
  palace_theme: string;
  total_locations: number;
  walkthrough: LociWalkthrough;
  full_narration: string;
  capture_id: string | null;
}

export interface LociRecallRequest {
  recalled_items: string[];
}

export interface LociRecallDetail {
  position: number;
  expected: string;
  recalled: string | null;
  correct: boolean;
  location_hint: string;
}

export interface LociRecallResponse {
  score: number;
  total: number;
  feedback: string;
  correct_order: string[];
  details: LociRecallDetail[];
}

export interface LociListItem {
  session_id: string;
  title: string;
  palace_theme: string;
  total_locations: number;
  last_recall_score: number | null;
  created_at: string;
}
