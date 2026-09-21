<script setup>
defineProps({
  modelValue: { type: String, required: true },
  disabled: { type: Boolean, default: false },
})
defineEmits(['update:modelValue'])
</script>

<template>
  <div class="field">
    <label for="ticket-question">궁금한 내용</label>
    <textarea
      id="ticket-question"
      :value="modelValue"
      :disabled="disabled"
      rows="4"
      placeholder="예: 일반예매 후 현장에서 티켓을 받을 때 무엇을 준비해야 해?"
      required
      @input="$emit('update:modelValue', $event.target.value)"
    />
  </div>
</template>
