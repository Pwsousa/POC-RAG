<script setup lang="ts">
import type { ResultData } from '../types/chat'

defineProps<{
  result: ResultData
}>()
</script>

<template>
  <section class="result-section">
    <div class="result-header">
      <span class="result-tag">
        {{ result.mode === 'qa' ? 'Pergunta' : 'Brief solicitado' }}
      </span>
      <p class="result-query">{{ result.query }}</p>
    </div>

    <div v-if="result.disclaimer" class="disclaimer-box">
      {{ result.disclaimer }}
    </div>

    <div class="response-card">
      <p class="response-text">
        <template v-for="(block, index) in result.blocks" :key="index">
          <span v-if="block.type === 'citation' && block.citationId">
            <em class="citation-text">{{ block.content }}</em>
            <span class="citation-marker">
              {{ block.citationId }}
            </span>
          </span>
          <span v-else>{{ block.content }}</span>
        </template>
      </p>
    </div>

    <div v-if="result.citations.length" class="references">
      <p class="references-title">Referências</p>
      <div class="references-list">
        <p v-for="citation in result.citations" :key="citation.id" class="reference-item">
          <span class="reference-id">[{{ citation.id }}]</span>
          {{ citation.document }}, p. {{ citation.page }}
          <span v-if="citation.section"> · §{{ citation.section }}</span>
          <span v-if="citation.url"> · <a :href="citation.url" target="_blank" rel="noopener noreferrer">link</a></span>
        </p>
      </div>
    </div>
  </section>
</template>
