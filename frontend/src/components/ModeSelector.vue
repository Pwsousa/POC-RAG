<script setup lang="ts">
import type { Mode } from '../types/chat'
import helpIcon from '../assets/material/help.svg'
import descriptionIcon from '../assets/material/description.svg'

const props = defineProps<{
  modelValue: Mode
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: Mode): void
}>()

const setMode = (value: Mode) => {
  if (value !== props.modelValue) {
    emit('update:modelValue', value)
  }
}
</script>

<template>
  <div class="mode-selector">
    <button
      class="mode-pill"
      :class="{ active: modelValue === 'qa' }"
      @click="setMode('qa')"
    >
      <img class="button-icon" :src="helpIcon" alt="" />
      Perguntar
    </button>
    <button
      class="mode-pill"
      :class="{ active: modelValue === 'brief' }"
      @click="setMode('brief')"
    >
      <img class="button-icon" :src="descriptionIcon" alt="" />
      Gerar Brief
    </button>
  </div>
</template>
