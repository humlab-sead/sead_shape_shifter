<template>
  <v-dialog v-model="dialogModel" max-width="500" persistent>
    <v-card>
      <v-card-title class="d-flex align-center text-error">
        <v-icon icon="mdi-alert-circle" class="mr-2" />
        <span>Confirm Deletion</span>
      </v-card-title>

      <v-card-text>
        <p class="text-body-1 mb-4">
          Are you sure you want to delete
          <strong>{{ itemType }} "{{ itemName }}"</strong>?
        </p>

        <v-alert type="warning" variant="tonal" density="compact"> This action cannot be undone. </v-alert>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="handleCancel" :disabled="loading"> Cancel </v-btn>
        <v-btn color="error" variant="flat" :loading="loading" @click="handleConfirm"> Delete </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Props {
  modelValue: boolean
  itemName?: string
  itemType?: string
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'confirm'): void
}

const props = withDefaults(defineProps<Props>(), {
  itemName: 'this item',
  itemType: 'item',
})

const emit = defineEmits<Emits>()

const loading = ref(false)

const dialogModel = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

async function handleConfirm() {
  loading.value = true
  try {
    emit('confirm')
    // Wait a moment for the action to complete
    await new Promise((resolve) => setTimeout(resolve, 300))
  } finally {
    loading.value = false
    dialogModel.value = false
  }
}

function handleCancel() {
  dialogModel.value = false
}
</script>
