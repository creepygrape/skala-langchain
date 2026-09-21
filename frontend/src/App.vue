<script setup>
import { onMounted, ref } from 'vue'

const backendStatus = ref('확인 중')
const hasError = ref(false)

async function checkBackend() {
  backendStatus.value = '확인 중'
  hasError.value = false

  try {
    const response = await fetch('/health')
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const data = await response.json()
    if (data.status !== 'ok') {
      throw new Error('Unexpected health response')
    }

    backendStatus.value = '연결됨'
  } catch {
    backendStatus.value = '연결 실패'
    hasError.value = true
  }
}

onMounted(checkBackend)
</script>

<template>
  <main class="container">
    <h1>맞춤형 콘서트 예매 가이드</h1>
    <p>서비스를 준비하고 있습니다.</p>

    <section class="health-card" aria-live="polite">
      <span>Backend</span>
      <strong :class="{ error: hasError }">{{ backendStatus }}</strong>
      <button v-if="hasError" type="button" @click="checkBackend">다시 확인</button>
    </section>
  </main>
</template>
