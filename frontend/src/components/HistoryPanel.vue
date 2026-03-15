<script setup lang="ts">
import type { ResultData } from '../types/chat'
import closeIcon from '../assets/material/close.svg'

defineProps<{
  visible: boolean
  items: ResultData[]
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'select', item: ResultData): void
}>()
</script>

<template>
  <div v-if="visible" class="history-overlay">
    <div class="history-backdrop" @click="emit('close')"></div>
    <aside class="history-panel">
      <div class="history-header">
        <p class="history-title">Histórico</p>
        <button class="history-close" @click="emit('close')">
          <img class="button-icon" :src="closeIcon" alt="Fechar" />
        </button>
      </div>
      <div v-if="!items.length" class="history-empty">
        Nenhuma consulta ainda.
      </div>
      <div v-else class="history-list">
        <button
          v-for="item in items"
          :key="item.id"
          class="history-item"
          @click="emit('select', item)"
        >
          <span class="history-meta">
            {{ item.mode === 'qa' ? 'Q&A' : 'Brief' }} · {{ item.timestamp }}
          </span>
          <span class="history-query">{{ item.query }}</span>
        </button>
      </div>
    </aside>
  </div>
</template>
