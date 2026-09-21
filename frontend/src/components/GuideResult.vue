<script setup>
defineProps({ guide: { type: Object, required: true } })

const sections = [
  { key: 'schedule', title: '일정', icon: '01' },
  { key: 'requirements', title: '준비사항', icon: '02' },
  { key: 'ticket_info', title: '티켓 정보', icon: '03' },
  { key: 'warnings', title: '주의사항', icon: '04' },
]
</script>

<template>
  <section class="result" aria-live="polite">
    <div class="result-heading">
      <p class="eyebrow">PERSONAL GUIDE</p>
      <h2>맞춤형 예매 안내</h2>
    </div>
    <article class="summary-card">
      <span>핵심 안내</span>
      <p>{{ guide.summary }}</p>
    </article>
    <div class="result-grid">
      <article v-for="section in sections" :key="section.key" class="result-card">
        <div class="card-title"><span>{{ section.icon }}</span><h3>{{ section.title }}</h3></div>
        <ul v-if="guide[section.key]?.length">
          <li v-for="item in guide[section.key]" :key="item">{{ item }}</li>
        </ul>
        <p v-else class="empty">관련 안내가 없습니다.</p>
      </article>
    </div>
    <article class="sources-card">
      <h3>참고 근거</h3>
      <ul v-if="guide.sources?.length">
        <li v-for="source in guide.sources" :key="source">
          <a :href="source" target="_blank" rel="noreferrer">{{ source }}</a>
        </li>
      </ul>
      <p v-else class="empty">표시할 출처가 없습니다.</p>
    </article>
  </section>
</template>
