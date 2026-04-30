export type AgeCode = 1 | 18 | 25 | 35 | 45 | 50 | 56

export type Gender = 'M' | 'F'

export type PathValue =
  | 'warm'
  | 'cold_request_profile'
  | 'cold_stored_demographics'
  | 'cold_fallback_genre_popular'

export interface ColdStartProfile {
  age_code: AgeCode
  gender: Gender
  occupation_code: number
  preferred_genres: string[]
}

export interface RecommendationRequest {
  user_id: string
  count: number
  profile?: ColdStartProfile
}

export interface MovieRecommendation {
  rank: number
  movie_id: number
  title: string
  genres: string[]
  score: number
}

export interface RecommendationResponse {
  user_id: string
  path: PathValue
  count_requested: number
  count_returned: number
  explanation: string
  recommendations: MovieRecommendation[]
  notes: string[]
}

export interface CodeLabel {
  code: number
  label: string
}

export interface ReferenceDataResponse {
  genres: string[]
  age_codes: CodeLabel[]
  occupation_codes: CodeLabel[]
  genders: string[]
}
