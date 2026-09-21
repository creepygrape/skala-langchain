<script setup>
import { ref } from 'vue'
import { createTicketGuide } from '../api/ticketGuideApi'
import GuideResult from '../components/GuideResult.vue'
import QuestionInput from '../components/QuestionInput.vue'
import UrlInput from '../components/UrlInput.vue'

const url = ref('')
const question = ref('')
const guide = ref(null)
const errorMessage = ref('')
const isLoading = ref(false)

async function submitGuide() {
  errorMessage.value = ''
  guide.value = null
  isLoading.value = true
  try {
    guide.value = await createTicketGuide({
      url: url.value.trim(),
      question: question.value.trim(),
    })
  } catch (error) {
    errorMessage.value = error instanceof Error
      ? error.message
      : '예매 정보를 확인하지 못했습니다.'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <main class="page-shell">
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">CONCERT TICKET ASSISTANT</p>
        <h1>복잡한 예매 공지에서<br /><em>내게 필요한 것만.</em></h1>
        <p class="hero-description">
          NOL Ticket 주소와 궁금한 내용을 입력하면 선예매, 티켓 수령,
          준비사항을 공연 공지에 근거해 정리해드려요.
        </p>
      </div>
      <form class="guide-form" @submit.prevent="submitGuide">
        <UrlInput v-model="url" :disabled="isLoading" />
        <QuestionInput v-model="question" :disabled="isLoading" />
        <button class="submit-button" type="submit" :disabled="isLoading">
          <span v-if="isLoading" class="spinner" aria-hidden="true"></span>
          {{ isLoading ? '공연 공지를 확인하고 있어요' : '맞춤형 예매 정보 확인' }}
        </button>
        <p v-if="errorMessage" class="error-message" role="alert">{{ errorMessage }}</p>
      </form>
    </section>
    <GuideResult v-if="guide" :guide="guide" />
  </main>
</template>
