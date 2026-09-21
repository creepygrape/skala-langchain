<script setup>
defineProps({
  modelValue: { type: String, required: true },
  disabled: { type: Boolean, default: false },
})
defineEmits(['update:modelValue'])
</script>

<template>
  <div class="field">
    <label for="ticket-url">예매 URL</label>
    <input
      id="ticket-url"
      :value="modelValue"
      :disabled="disabled"
      type="url"
      inputmode="url"
      autocomplete="url"
      placeholder="https://nol.yanolja.com/ticket/products/26012624"
      required
      @input="$emit('update:modelValue', $event.target.value)"
    />
    <p class="field-hint">NOL Ticket 콘서트 상품 URL을 입력해주세요.</p>
  </div>
</template>
