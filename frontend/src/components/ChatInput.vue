<script setup lang="ts">
import type { Mode } from '../types/chat'
import sendIcon from '../assets/material/send.svg'

const props = defineProps<{
  modelValue: string
  mode: Mode
  isProcessing: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'submit'): void
}>()

const onKeyDown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    emit('submit')
  }
}

const onSubmit = () => {
  emit('submit')
}
</script>

<template>
  <div class="chat-input">
    <div class="input-card">
      <textarea
        class="input-field"
        :value="modelValue"
        :placeholder="mode === 'qa' ? 'Pergunte sobre mudanças climáticas...' : 'Qual tema para o brief? Ex: Emissões de CO₂'"
        :disabled="isProcessing"
        rows="1"
        @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
        @keydown="onKeyDown"
      ></textarea>
      <button
        class="send-button"
        :disabled="!modelValue.trim() || isProcessing"
        @click="onSubmit"
      >
        <img class="send-icon" :src="sendIcon" alt="Enviar" />
      </button>
    </div>
    <p class="input-footnote">
      Respostas baseadas nos relatórios IPCC AR6 · Todas as afirmações incluem citações
    </p>
  </div>
</template>
