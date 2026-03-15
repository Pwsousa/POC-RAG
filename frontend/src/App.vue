<script setup lang="ts">
import { ref } from 'vue'
import type { Mode, ResultData, AnswerBlock, Citation } from './types/chat'
import HeaderBar from './components/HeaderBar.vue'
import EmptyState from './components/EmptyState.vue'
import ModeSelector from './components/ModeSelector.vue'
import ChatInput from './components/ChatInput.vue'
import ResponseCard from './components/ResponseCard.vue'
import HistoryPanel from './components/HistoryPanel.vue'

const mode = ref<Mode>('qa')
const query = ref('')
const isProcessing = ref(false)
const currentResult = ref<ResultData | null>(null)
const history = ref<ResultData[]>([])
const showHistory = ref(false)

const MOCK_QA: { blocks: AnswerBlock[]; citations: Citation[]; disclaimer: string } = {
  disclaimer:
    'Projeções climáticas contêm incertezas inerentes. Este sistema não substitui a leitura integral dos relatórios do IPCC.',
  citations: [
    {
      id: 1,
      text: 'Global mean sea level rose by 0.20 [0.15 to 0.25] m between 1901 and 2018.',
      document: 'IPCC AR6 WG1 — Summary for Policymakers',
      page: 5,
      section: 'A.1.7'
    },
    {
      id: 2,
      text: 'Global mean sea level will continue to rise over the 21st century under all considered SSP scenarios.',
      document: 'IPCC AR6 WG1 — Summary for Policymakers',
      page: 28,
      section: 'B.5.3'
    },
    {
      id: 3,
      text: 'By 2100, global mean sea level rise is likely in the range of 0.28–0.55 m under SSP1-1.9 and 0.63–1.01 m under SSP5-8.5.',
      document: 'IPCC AR6 WG1 — Chapter 9',
      page: 1302,
      section: '9.6.3'
    }
  ],
  blocks: [
    {
      type: 'text',
      content:
        'O nível médio global do mar apresentou elevação significativa ao longo do último século. Segundo o Grupo de Trabalho I do AR6, '
    },
    {
      type: 'citation',
      content: 'o nível médio global do mar subiu 0,20 [0,15 a 0,25] m entre 1901 e 2018',
      citationId: 1
    },
    { type: 'text', content: '. As projeções indicam continuidade dessa tendência: ' },
    {
      type: 'citation',
      content:
        'o nível médio global do mar continuará a subir ao longo do século XXI sob todos os cenários SSP considerados',
      citationId: 2
    },
    {
      type: 'text',
      content:
        '.\n\nAs estimativas variam conforme o cenário. No cenário de maior mitigação (SSP1-1.9), a elevação projetada até 2100 é de 0,28 a 0,55 m. No cenário de altas emissões (SSP5-8.5), '
    },
    {
      type: 'citation',
      content: 'a elevação provável está na faixa de 0,63 a 1,01 m até 2100',
      citationId: 3
    },
    {
      type: 'text',
      content:
        '. Esses valores não incluem processos de instabilidade de mantos de gelo que poderiam ampliar a elevação.'
    }
  ]
}

const MOCK_BRIEF: { blocks: AnswerBlock[]; citations: Citation[]; disclaimer: string } = {
  disclaimer:
    'Brief gerado automaticamente. Verificar dados nas fontes originais antes de uso em publicações.',
  citations: [
    {
      id: 1,
      text: 'Global net anthropogenic GHG emissions have continued to rise during the period 2010–2019.',
      document: 'IPCC AR6 WG3 — SPM',
      page: 4,
      section: 'B.1'
    },
    {
      id: 2,
      text: 'Net anthropogenic CO₂ emissions in the period 2010–2019 were higher than in any previous decade.',
      document: 'IPCC AR6 WG3 — SPM',
      page: 6,
      section: 'B.1.1'
    }
  ],
  blocks: [
    {
      type: 'text',
      content:
        'As emissões antropogênicas globais de gases de efeito estufa mantiveram trajetória de crescimento na última década. '
    },
    {
      type: 'citation',
      content:
        'as emissões líquidas antropogênicas de GEE continuaram a subir durante o período 2010–2019',
      citationId: 1
    },
    { type: 'text', content: '. Especificamente para o CO₂, ' },
    {
      type: 'citation',
      content:
        'as emissões líquidas antropogênicas de CO₂ no período 2010–2019 foram maiores que em qualquer década anterior',
      citationId: 2
    },
    {
      type: 'text',
      content:
        '.\n\nSetores de energia e indústria permanecem como principais fontes de emissão, com transporte e agricultura como contribuintes significativos.'
    }
  ]
}

const handleSubmit = () => {
  if (!query.value.trim() || isProcessing.value) return
  const q = query.value.trim()
  query.value = ''
  isProcessing.value = true

  setTimeout(() => {
    const mock = mode.value === 'qa' ? MOCK_QA : MOCK_BRIEF
    const result: ResultData = {
      id: crypto.randomUUID(),
      query: q,
      mode: mode.value,
      blocks: mock.blocks,
      citations: mock.citations,
      disclaimer: mock.disclaimer,
      timestamp: new Date().toLocaleDateString('pt-BR')
    }
    currentResult.value = result
    history.value = [result, ...history.value]
    isProcessing.value = false
  }, 1500)
}

const handleSelectHistory = (item: ResultData) => {
  currentResult.value = item
  showHistory.value = false
}
</script>

<template>
  <div class="page">
    <HeaderBar :show-history="showHistory" @toggle-history="showHistory = !showHistory" />
    <main class="content">
      <EmptyState v-if="!currentResult && !isProcessing" />
      <div v-else class="results">
        <div v-if="isProcessing" class="loading">
          <div class="loading-dot"></div>
          <p>Recuperando evidências dos relatórios...</p>
        </div>
        <ResponseCard v-else-if="currentResult" :result="currentResult" />
      </div>
      <ModeSelector v-model="mode" />
      <ChatInput v-model="query" :mode="mode" :is-processing="isProcessing" @submit="handleSubmit" />
    </main>
    <HistoryPanel
      :visible="showHistory"
      :items="history"
      @close="showHistory = false"
      @select="handleSelectHistory"
    />
  </div>
</template>
