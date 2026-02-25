<template>
  <div class="rag-workbench page-view">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card shadow="hover" class="builder-card">
          <template #header>
            <div class="card-header">RAG 建库</div>
          </template>

          <el-form label-position="top">
            <el-form-item label="选择文件">
              <el-upload
                :auto-upload="false"
                :limit="1"
                :on-change="handleFileChange"
                :on-remove="handleFileRemove"
                accept=".pdf,.txt,.docx"
              >
                <el-button type="primary">选择文件</el-button>
              </el-upload>
            </el-form-item>

            <el-form-item label="书本标签（可选）">
              <el-input v-model="bookLabel" placeholder="如：民法学（第二版）" />
            </el-form-item>

            <el-form-item label="分块大小">
              <el-input-number v-model="chunkSize" :min="200" :max="3000" :step="100" />
            </el-form-item>

            <el-form-item label="分块重叠">
              <el-input-number v-model="chunkOverlap" :min="0" :max="1000" :step="50" />
            </el-form-item>

            <el-button type="primary" :loading="indexing" @click="handleIndexFile" style="width: 100%">
              {{ indexing ? '建库中...' : '上传并建立索引' }}
            </el-button>
          </el-form>

          <el-alert
            v-if="lastIndexResult"
            :type="lastIndexResult.success ? 'success' : 'error'"
            :title="lastIndexResult.message"
            :closable="false"
            style="margin-top: 16px"
          >
            <template #default>
              <div>chunk: {{ lastIndexResult.chunk_count }}，doc: {{ lastIndexResult.doc_count }}</div>
              <div v-if="lastIndexResult.book_label">标签: {{ lastIndexResult.book_label }}</div>
            </template>
          </el-alert>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card shadow="hover" class="library-card">
          <template #header>
            <div class="card-header actions">
              <span>RAG 库列表</span>
              <el-button text type="primary" :loading="loadingBooks" @click="loadBooks">刷新</el-button>
            </div>
          </template>

          <el-table :data="books" border stripe v-loading="loadingBooks">
            <el-table-column prop="book_label" label="书本标签" min-width="220" />
            <el-table-column prop="file_name" label="来源文件" min-width="220">
              <template #default="{ row }">
                {{ row.file_name || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="book_id" label="Book ID" min-width="220" />
            <el-table-column prop="chunk_count" label="分块数" width="100" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, type UploadFile, type UploadFiles } from 'element-plus'
import { ragAiApi, type RagBookItem, type RagIndexData } from '../api'

const selectedFile = ref<File | null>(null)
const bookLabel = ref('')
const chunkSize = ref(1000)
const chunkOverlap = ref(200)
const indexing = ref(false)
const lastIndexResult = ref<RagIndexData | null>(null)

const books = ref<RagBookItem[]>([])
const loadingBooks = ref(false)

const handleFileChange = (file: UploadFile, _files: UploadFiles) => {
  selectedFile.value = file.raw || null
}

const handleFileRemove = () => {
  selectedFile.value = null
}

const loadBooks = async () => {
  loadingBooks.value = true
  try {
    const result = await ragAiApi.listBooks()
    if (!result.success) {
      throw new Error(result.message || '查询失败')
    }
    books.value = result.items || []
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '查询 RAG 库失败')
  } finally {
    loadingBooks.value = false
  }
}

const handleIndexFile = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  indexing.value = true
  try {
    const result = await ragAiApi.indexByFile({
      file: selectedFile.value,
      chunkSize: chunkSize.value,
      chunkOverlap: chunkOverlap.value,
      bookLabel: bookLabel.value
    })
    lastIndexResult.value = result
    if (result.success) {
      ElMessage.success('RAG 索引完成')
      await loadBooks()
    } else {
      ElMessage.error(result.message || '索引失败')
    }
  } catch (_error) {
    ElMessage.error('调用 RAG 索引接口失败')
  } finally {
    indexing.value = false
  }
}

onMounted(() => {
  loadBooks()
})
</script>

<style scoped lang="scss">
.rag-workbench {
  :deep(.el-row) {
    flex-wrap: nowrap;
  }

  .card-header {
    font-weight: 620;
    color: var(--text-primary);

    &.actions {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }

  .builder-card,
  .library-card {
    border-radius: 16px;
  }

  :deep(.el-alert) {
    border-radius: 12px;
  }

  :deep(.el-upload) {
    width: 100%;
  }

  :deep(.el-upload .el-button) {
    width: 100%;
  }

  :deep(.el-form-item__label) {
    font-weight: 520;
    color: var(--text-secondary);
  }
}
</style>
