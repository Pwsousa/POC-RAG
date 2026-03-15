export type Mode = 'qa' | 'brief'

export interface AnswerBlock {
  type: 'text' | 'citation'
  content: string
  citationId?: number
}

export interface Citation {
  id: number
  text: string
  document: string
  page: number
  section?: string
}

export interface ResultData {
  id: string
  query: string
  mode: Mode
  blocks: AnswerBlock[]
  citations: Citation[]
  disclaimer?: string
  timestamp: string
}
