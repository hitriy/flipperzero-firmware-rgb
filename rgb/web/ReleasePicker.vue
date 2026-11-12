<template>
  <div class="q-my-md" style="width: 100%; max-width: 620px">
    <q-select
      v-model="selected"
      :options="options"
      :disable="disabled || !releases.length"
      label="Firmware version"
      outlined
      emit-value
      map-options
      @update:model-value="choose"
    />
    <p v-if="error" role="alert" class="text-negative q-mt-sm">{{ error }}</p>
    <p v-if="current" class="q-mt-md q-mb-none">
      <a :href="current.release_url" target="_blank" rel="noopener">Release notes and downloads</a>
      · <a :href="current.bundle_url">Download selected update</a>
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

defineProps<{ disabled?: boolean }>()
const emit = defineEmits<{ selected: [tag: string] }>()
type Release = { tag: string; release_url: string; bundle_url: string }
const releases = ref<Release[]>([])
const selected = ref('')
const error = ref('')
const options = computed(() => releases.value.map((release, index) => ({
  label: `${release.tag}${index === 0 ? ' (latest)' : ''}`,
  value: release.tag
})))
const current = computed(() => releases.value.find(release => release.tag === selected.value))

const choose = (tag: string) => {
  if (!releases.value.some(release => release.tag === tag)) return
  sessionStorage.setItem('rgb-version', tag)
  emit('selected', tag)
}

onMounted(async () => {
  try {
    const response = await fetch(`${process.env.RGB_PUBLIC_PATH}channels.json`, { cache: 'no-cache' })
    if (!response.ok) throw new Error('Unable to load firmware versions. Please reload.')
    const data = await response.json()
    releases.value = data.releases
    const saved = sessionStorage.getItem('rgb-version')
    selected.value = releases.value.find(release => release.tag === saved)?.tag || releases.value[0]?.tag || ''
    if (!selected.value) throw new Error('No published RGB firmware is available.')
    choose(selected.value)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause)
  }
})
</script>
