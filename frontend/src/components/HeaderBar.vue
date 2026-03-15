<script setup lang="ts">
import ecoIcon from '../assets/material/eco.svg'
import historyIcon from '../assets/material/history.svg'

defineProps<{
  showHistory: boolean
}>()

const emit = defineEmits<{
  (e: 'toggle-history'): void
}>()
</script>

<template>
  <header class="header">
    <div class="brand">
      <img class="brand-icon" :src="ecoIcon" alt="Clima" />
      <span class="brand-title">Clima em Foco</span>
    </div>
    <button class="history-button" @click="emit('toggle-history')">
      <img class="button-icon" :src="historyIcon" alt="" />
      Histórico
    </button>
  </header>
</template>
