<script setup lang="ts">
import ecoIcon from '../assets/material/eco.svg'
</script>

<template>
  <section class="empty-state">
    <div class="empty-icon">
      <img class="icon-large" :src="ecoIcon" alt="Clima" />
    </div>
    <h1>Clima em Foco</h1>
    <p class="empty-subtitle">
      Pergunte sobre mudanças climáticas e receba respostas com citações diretas dos relatórios do IPCC AR6.
    </p>
  </section>
</template>
