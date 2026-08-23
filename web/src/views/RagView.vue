<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { CheckCircle2, FileText, LoaderCircle, RefreshCw, Search, Trash2, TriangleAlert, UploadCloud, X } from "lucide-vue-next";
import { ApiRequestError, deleteKnowledgeDocument, fetchKnowledgeDocuments, uploadKnowledgeDocument } from "@/api/client";
import ConfirmDialog from "@/components/ConfirmDialog.vue";
import { getDemoRole } from "@/auth/auth";
import type { KnowledgeDocument, KnowledgeDocumentStatus } from "@/types/api";

const documents = ref<KnowledgeDocument[]>([]);
const loading = ref(true);
const refreshing = ref(false);
const saving = ref(false);
const deleting = ref(false);
const errorMessage = ref("");
const query = ref("");
const categoryFilter = ref("all");
const uploadOpen = ref(false);
const deleteTarget = ref<KnowledgeDocument | null>(null);
const selectedFile = ref<File | null>(null);
const category = ref("业务规则");
const fileInput = ref<HTMLInputElement | null>(null);
let pollTimer: number | undefined;

const isAdmin = computed(() => getDemoRole() === "super_admin");
const categories = computed(() => Array.from(new Set(documents.value.map((item) => item.category))).sort());
const filteredDocuments = computed(() => {
  const needle = query.value.trim().toLowerCase();
  return documents.value.filter((document) => {
    const matchesCategory = categoryFilter.value === "all" || document.category === categoryFilter.value;
    const matchesQuery = !needle || `${document.filename} ${document.category} ${document.summary}`.toLowerCase().includes(needle);
    return matchesCategory && matchesQuery;
  });
});
const indexedCount = computed(() => documents.value.filter((item) => item.status === "indexed").length);
const processingCount = computed(() => documents.value.filter((item) => item.status === "uploading" || item.status === "parsing").length);
const failedCount = computed(() => documents.value.filter((item) => item.status === "failed").length);

function setError(error: unknown, fallback: string) { errorMessage.value = error instanceof ApiRequestError ? error.message : fallback; }
async function loadDocuments(silent = false) {
  if (silent) refreshing.value = true; else loading.value = true;
  errorMessage.value = "";
  try { documents.value = await fetchKnowledgeDocuments(); } catch (error) { setError(error, "资料库加载失败。"); }
  finally { loading.value = false; refreshing.value = false; syncPolling(); }
}
function syncPolling() {
  const active = documents.value.some((item) => item.status === "uploading" || item.status === "parsing");
  if (active && pollTimer === undefined) pollTimer = window.setInterval(() => void loadDocuments(true), 2000);
  if (!active && pollTimer !== undefined) { window.clearInterval(pollTimer); pollTimer = undefined; }
}
function openUpload() { selectedFile.value = null; category.value = "业务规则"; errorMessage.value = ""; uploadOpen.value = true; }
function closeUpload() { if (!saving.value) uploadOpen.value = false; }
function chooseFile(file: File | undefined) {
  if (!file) return;
  const allowed = [".txt", ".md", ".pdf", ".docx", ".csv"];
  const suffix = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  if (!allowed.includes(suffix)) { errorMessage.value = "仅支持 TXT、MD、PDF、DOCX 和 CSV 文件。"; return; }
  if (file.size > 20 * 1024 * 1024) { errorMessage.value = "文件大小不能超过 20 MiB。"; return; }
  errorMessage.value = ""; selectedFile.value = file;
}
function handleDrop(event: DragEvent) { event.preventDefault(); chooseFile(event.dataTransfer?.files?.[0]); }
async function saveUpload() {
  if (!selectedFile.value) { errorMessage.value = "请选择要上传的文件。"; return; }
  saving.value = true; errorMessage.value = "";
  try {
    const document = await uploadKnowledgeDocument(selectedFile.value, category.value.trim() || "未分类");
    documents.value = [document, ...documents.value.filter((item) => item.id !== document.id)];
    uploadOpen.value = false; syncPolling();
  } catch (error) { setError(error, "文档上传失败。"); }
  finally { saving.value = false; }
}
function openDelete(document: KnowledgeDocument) { deleteTarget.value = document; errorMessage.value = ""; }
function closeDelete() { if (!deleting.value) deleteTarget.value = null; }
async function removeDocument() {
  const document = deleteTarget.value;
  if (!document || deleting.value) return;
  deleting.value = true; errorMessage.value = "";
  try { await deleteKnowledgeDocument(document.id); documents.value = documents.value.filter((item) => item.id !== document.id); deleteTarget.value = null; }
  catch (error) { setError(error, "文档删除失败。"); }
  finally { deleting.value = false; }
}
function statusLabel(status: KnowledgeDocumentStatus) { return { uploading: "上传中", parsing: "解析中", indexed: "已索引", failed: "失败" }[status]; }
function formatSize(bytes: number) { if (bytes < 1024) return `${bytes} B`; if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`; return `${(bytes / 1024 / 1024).toFixed(1)} MB`; }
function formatDate(value: string) { const date = new Date(value); return Number.isNaN(date.getTime()) ? "-" : new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium" }).format(date); }
onMounted(() => void loadDocuments());
onBeforeUnmount(() => { if (pollTimer !== undefined) window.clearInterval(pollTimer); });
</script>

<template>
  <main class="rag-page">
    <header class="page-header"><div><p class="eyebrow">KNOWLEDGE BASE</p><h1>RAG 资料库</h1><p class="page-description">管理业务规则、指标口径和操作文档，为 Agent 提供可追溯的业务背景。</p></div><button v-if="isAdmin" class="primary-button" type="button" @click="openUpload"><UploadCloud :size="17" />上传资料</button></header>
    <section class="summary-row" aria-label="资料库概览"><div class="summary-item"><strong>{{ documents.length }}</strong><span>资料总数</span></div><div class="summary-item"><strong>{{ indexedCount }}</strong><span>已完成索引</span></div><div class="summary-item"><strong>{{ processingCount }}</strong><span>处理中</span></div><div class="summary-item"><strong>{{ failedCount }}</strong><span>需要处理</span></div></section>
    <p v-if="errorMessage && !uploadOpen && !deleteTarget" class="alert" role="alert">{{ errorMessage }}</p>
    <section class="knowledge-surface" aria-labelledby="knowledge-title">
      <div class="surface-heading"><div><h2 id="knowledge-title">资料列表</h2><p>已索引内容会自动参与 Agent 的业务背景检索。</p></div><button class="icon-button" type="button" title="刷新列表" aria-label="刷新列表" :disabled="loading || refreshing" @click="loadDocuments(true)"><RefreshCw :class="{ spin: loading || refreshing }" :size="17" /></button></div>
      <div class="filters"><label class="search-field"><Search :size="16" /><input v-model="query" type="search" placeholder="搜索文件名、分类或摘要" aria-label="搜索资料" /></label><select v-model="categoryFilter" aria-label="按分类筛选"><option value="all">全部分类</option><option v-for="item in categories" :key="item" :value="item">{{ item }}</option></select></div>
      <div v-if="loading" class="empty-state"><LoaderCircle class="spin" :size="22" />正在加载资料库</div><div v-else-if="!filteredDocuments.length" class="empty-state"><FileText :size="22" />{{ documents.length ? "没有匹配的资料" : "暂无资料，先上传一份业务文档" }}</div>
      <div v-else class="document-list"><article v-for="document in filteredDocuments" :key="document.id" class="document-row"><span class="document-icon"><FileText :size="19" /></span><div class="document-main"><div class="document-title"><h3>{{ document.filename }}</h3><span class="file-type">{{ document.file_type }}</span></div><p>{{ document.summary || "等待解析摘要" }}</p><small>{{ document.category }} · {{ formatSize(document.size_bytes) }} · {{ formatDate(document.created_at) }}<template v-if="document.chunk_count"> · {{ document.chunk_count }} 个片段</template></small><div v-if="document.failure_message" class="failure-message"><TriangleAlert :size="14" />{{ document.failure_message }}</div></div><span :class="['status-badge', `status-badge--${document.status}`]"><LoaderCircle v-if="document.status === 'uploading' || document.status === 'parsing'" class="spin" :size="13" /><CheckCircle2 v-else-if="document.status === 'indexed'" :size="13" /><TriangleAlert v-else :size="13" />{{ statusLabel(document.status) }}</span><button v-if="isAdmin" class="icon-button icon-button--danger" type="button" title="删除资料" aria-label="删除资料" :disabled="document.status === 'uploading' || document.status === 'parsing'" @click="openDelete(document)"><Trash2 :size="16" /></button></article></div>
    </section>
    <div v-if="uploadOpen" class="modal-backdrop" role="presentation" @click.self="closeUpload"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="upload-title"><header class="modal-header"><div><p class="modal-eyebrow">NEW DOCUMENT</p><h2 id="upload-title">上传资料</h2></div><button class="icon-button" type="button" aria-label="关闭" title="关闭" @click="closeUpload"><X :size="19" /></button></header><form class="upload-form" @submit.prevent="saveUpload"><button class="drop-zone" type="button" @click="fileInput?.click()" @dragover.prevent @drop="handleDrop"><UploadCloud :size="25" /><strong>{{ selectedFile ? selectedFile.name : "拖拽文件到这里，或点击选择" }}</strong><small>支持 TXT、MD、PDF、DOCX、CSV，最大 20 MiB</small></button><input ref="fileInput" class="sr-only" type="file" accept=".txt,.md,.pdf,.docx,.csv" @change="chooseFile(($event.target as HTMLInputElement).files?.[0])" /><label>分类<input v-model="category" type="text" maxlength="80" placeholder="例如：业务规则" :disabled="saving" /></label><p v-if="errorMessage && uploadOpen" class="form-error" role="alert">{{ errorMessage }}</p><footer class="modal-actions"><button class="secondary-button" type="button" :disabled="saving" @click="closeUpload">取消</button><button class="primary-button" type="submit" :disabled="saving"><LoaderCircle v-if="saving" class="spin" :size="16" />{{ saving ? "上传中" : "开始上传" }}</button></footer></form></section></div>
    <ConfirmDialog :open="Boolean(deleteTarget)" title="删除资料" confirm-text="删除资料" busy-text="删除中" :busy="deleting" :error="errorMessage" @update:open="closeDelete" @confirm="removeDocument"><template #icon><Trash2 :size="18" /></template><template #description>确定要删除“{{ deleteTarget?.filename }}”吗？索引内容也会一并移除。</template></ConfirmDialog>
  </main>
</template>

<style scoped>
.rag-page{min-height:100dvh;padding:30px clamp(20px,5vw,72px) 56px;color:#203027;background:#f7f9f7}.page-header,.surface-heading,.document-row,.document-title,.modal-header,.modal-actions{display:flex;align-items:center;justify-content:space-between;gap:18px}.page-header{align-items:flex-end;margin-bottom:28px}.eyebrow,.modal-eyebrow{margin:0 0 9px;color:#4c9065;font-size:10px;font-weight:800;letter-spacing:.14em}.modal-eyebrow{color:#8b8b88}h1,h2,h3,p{margin-top:0}h1{margin-bottom:8px;font-size:30px}h2{margin-bottom:0;font-size:18px}.page-description,.surface-heading p{margin-bottom:0;color:#718077;font-size:13px}.primary-button,.secondary-button{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:40px;border-radius:7px;padding:0 14px;font-size:13px;font-weight:750;cursor:pointer}.primary-button{border:0;color:#143322;background:#b7e7cb}.primary-button:hover{background:#a6dbb9}.secondary-button{border:1px solid #d9e0db;color:#55645b;background:#fff}.primary-button:disabled,.secondary-button:disabled,.icon-button:disabled{opacity:.55;cursor:default}.summary-row{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;margin-bottom:20px;border:1px solid #e0e7e2;background:#e0e7e2}.summary-item{display:grid;gap:6px;padding:17px 21px;background:#fff}.summary-item strong{font-size:21px}.summary-item span{color:#7d8a82;font-size:11px}.alert,.form-error{margin:16px 0;border:1px solid #f0c8c8;border-radius:6px;padding:11px 13px;color:#a24a4a;background:#fff7f7;font-size:13px}.knowledge-surface{border:1px solid #e0e7e2;background:#fff}.surface-heading{padding:21px 24px;border-bottom:1px solid #edf0ed}.surface-heading p{margin-top:6px}.filters{display:flex;gap:10px;padding:14px 24px;border-bottom:1px solid #edf0ed}.search-field{display:flex;flex:1;align-items:center;gap:8px;border:1px solid #dce4dd;border-radius:6px;padding:0 10px;color:#7b887f}.search-field input,.filters select{height:36px;border:0;outline:0;color:#3f5045;background:#fff;font-size:12px}.search-field input{width:100%}.filters select{min-width:130px;border:1px solid #dce4dd;border-radius:6px;padding:0 9px}.document-list{display:grid;padding:8px 24px 22px}.document-row{min-width:0;align-items:flex-start;border-bottom:1px solid #edf0ed;padding:16px 0}.document-row:last-child{border-bottom:0}.document-icon{display:grid;width:37px;height:37px;flex:0 0 auto;place-items:center;border-radius:8px;color:#397453;background:#e8f4eb}.document-main{min-width:0;flex:1}.document-title{justify-content:flex-start;gap:8px}.document-title h3{overflow:hidden;margin:0;color:#304337;font-size:14px;text-overflow:ellipsis;white-space:nowrap}.file-type{border-radius:4px;padding:3px 5px;color:#748078;background:#f0f4f1;font-size:9px;font-weight:800}.document-main p{overflow:hidden;margin:6px 0;color:#7d8a82;font-size:12px;text-overflow:ellipsis;white-space:nowrap}.document-main small{color:#9aa49e;font-size:10px}.status-badge{display:inline-flex;flex:0 0 auto;align-items:center;gap:5px;border-radius:999px;padding:5px 9px;color:#9a6e34;background:#fff4df;font-size:11px;font-weight:700}.status-badge--indexed{color:#397453;background:#e8f4eb}.status-badge--failed{color:#a24a4a;background:#fff0f0}.failure-message{display:flex;align-items:center;gap:5px;margin-top:8px;color:#a24a4a;font-size:11px}.icon-button{display:inline-grid;width:32px;height:32px;flex:0 0 auto;place-items:center;border:0;border-radius:6px;color:#64736a;background:transparent;cursor:pointer}.icon-button:hover:not(:disabled){color:#326d4c;background:#eef5ef}.icon-button--danger:hover:not(:disabled){color:#b65353;background:#fff0f0}.empty-state{display:flex;min-height:220px;align-items:center;justify-content:center;gap:9px;color:#7b887f;font-size:13px}.spin{animation:spin .8s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}.modal-backdrop{position:fixed;z-index:100;inset:0;display:grid;place-items:center;padding:24px;background:rgba(22,37,29,.35)}.modal{width:min(100%,470px);border:1px solid #dfe7e1;border-radius:9px;padding:24px;background:#fff;box-shadow:0 24px 70px rgba(22,37,29,.22)}.modal-header{align-items:flex-start;margin-bottom:23px}.upload-form{display:grid;gap:15px}.drop-zone{display:grid;min-height:150px;place-items:center;gap:8px;border:1px dashed #b9cfc0;border-radius:8px;padding:20px;color:#397453;background:#f8fcf9;cursor:pointer}.drop-zone strong{color:#355340;font-size:13px}.drop-zone small{color:#819087;font-size:11px}.upload-form label{display:grid;gap:7px;color:#4a5b50;font-size:12px;font-weight:700}.upload-form input[type=text]{width:100%;height:41px;border:1px solid #d9e2db;border-radius:6px;padding:0 10px;outline:0;color:#26382c;background:#fbfdfb;font-size:13px}.upload-form input:focus{border-color:#78b58b;box-shadow:0 0 0 3px rgba(104,181,130,.12)}.modal-actions{justify-content:flex-end;margin-top:4px}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap}@media(max-width:700px){.rag-page{padding:22px 16px 40px}.page-header{align-items:flex-start;flex-direction:column}.page-header .primary-button{width:100%}.summary-row{grid-template-columns:1fr 1fr}.summary-item{padding:14px}.filters{padding-inline:14px}.document-list{padding-inline:14px}.document-row{display:grid;grid-template-columns:auto 1fr auto;gap:10px}.document-row>.icon-button{grid-column:3;grid-row:1}.status-badge{grid-column:2/4;grid-row:2;justify-self:start}.modal-backdrop{padding:12px}}
</style>
