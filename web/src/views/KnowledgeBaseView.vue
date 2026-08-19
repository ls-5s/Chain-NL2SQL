<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import {
  Check,
  ChevronDown,
  FileArchive,
  FileText,
  FolderOpen,
  MoreHorizontal,
  Search,
  Trash2,
  Upload,
} from "lucide-vue-next";
import { deleteKnowledgeDocument, fetchKnowledgeDocuments, uploadKnowledgeDocument } from "@/api/client";
import type { KnowledgeDocument, KnowledgeDocumentStatus } from "@/types/api";

const items = ref<KnowledgeDocument[]>([]);
const category = ref("涓氬姟瑙勫垯");
const isLoading = ref(false);
const errorMessage = ref<string | null>(null);
const keyword = ref("");
const activeFilter = ref("鍏ㄩ儴璧勬枡");
const filters = ["鍏ㄩ儴璧勬枡", "涓氬姟瑙勫垯", "鎸囨爣鍙ｅ緞", "鏁版嵁瀛楀吀"];
const categories = ["涓氬姟瑙勫垯", "鎸囨爣鍙ｅ緞", "鏁版嵁瀛楀吀", "椤圭洰璧勬枡"];
const filteredItems = computed(() => {
  const term = keyword.value.trim().toLowerCase();
  return items.value.filter(
    (item) =>
      (activeFilter.value === "鍏ㄩ儴璧勬枡" || item.category === activeFilter.value) &&
      (!term ||
        [item.filename, item.category, item.summary].some((value) =>
          value.toLowerCase().includes(term),
        )),
  );
});
const indexedCount = computed(() => items.value.filter((item) => item.status === "indexed").length);
function statusCopy(status: KnowledgeDocumentStatus) {
  return { uploading: "涓婁紶涓?, parsing: "瑙ｆ瀽涓?, indexed: "宸插叆搴?, failed: "闇€澶勭悊" }[status];
}
function formatSize(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}
function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
async function loadDocuments() {
  isLoading.value = true;
  errorMessage.value = null;
  try {
    items.value = await fetchKnowledgeDocuments();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "璧勬枡鍔犺浇澶辫触锛岃绋嶅悗閲嶈瘯銆?;
  } finally {
    isLoading.value = false;
  }
}
async function handleUpload(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  errorMessage.value = null;
  try {
    const document = await uploadKnowledgeDocument(file, category.value);
    items.value = [document, ...items.value];
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "涓婁紶澶辫触锛岃绋嶅悗閲嶈瘯銆?;
  } finally {
    input.value = "";
  }
}
async function removeDocument(id: string) {
  errorMessage.value = null;
  try {
    await deleteKnowledgeDocument(id);
    items.value = items.value.filter((item) => item.id !== id);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "鍒犻櫎澶辫触锛岃绋嶅悗閲嶈瘯銆?;
  }
}
onMounted(loadDocuments);
</script>

<template>
  <section class="knowledge-page">
    <header class="page-heading">
      <div>
        <div class="breadcrumb"><span>宸ヤ綔绌洪棿</span><span>/</span><strong>鐭ヨ瘑搴?/strong></div>
        <h1>鐭ヨ瘑搴?/h1>
        <p>缁存姢涓氬姟瑙勫垯銆佹寚鏍囧彛寰勪笌鏁版嵁瀛楀吀锛屼负鏌ヨ鎻愪緵鍙潬鐨勮涔変笂涓嬫枃銆?/p>
      </div>
      <label class="upload-button"
        ><Upload :size="17" />涓婁紶璧勬枡<input
          type="file"
          accept=".txt,.md,.pdf,.docx,.csv"
          @change="handleUpload"
      /></label>
    </header>
    <div class="workspace-summary">
      <div class="summary-card">
        <span class="summary-card__icon"><FolderOpen :size="19" /></span>
        <div>
          <span>璧勬枡鎬绘暟</span><strong>{{ items.length }}</strong>
        </div>
      </div>
      <div class="summary-card">
        <span class="summary-card__icon summary-card__icon--green"><Check :size="19" /></span>
        <div>
          <span>宸插叆搴?/span><strong>{{ indexedCount }}</strong>
        </div>
      </div>
      <div class="workspace-summary__note"><span class="live-dot" />绱㈠紩鏈嶅姟杩愯姝ｅ父</div>
    </div>
    <div class="knowledge-toolbar">
      <div class="filter-tabs" role="tablist" aria-label="璧勬枡鍒嗙被">
        <button
          v-for="filter in filters"
          :key="filter"
          :class="{ 'filter-tab--active': activeFilter === filter }"
          role="tab"
          :aria-selected="activeFilter === filter"
          @click="activeFilter = filter"
        >
          {{ filter }}
        </button>
      </div>
      <div class="toolbar-actions">
        <label class="category-select"
          ><span>褰掔被涓?/span
          ><select v-model="category" aria-label="涓婁紶璧勬枡鐨勫垎绫?>
            <option v-for="option in categories" :key="option" :value="option">
              {{ option }}
            </option></select
          ><ChevronDown :size="14" /></label
        ><label class="document-search"
          ><Search :size="16" /><input v-model="keyword" type="search" placeholder="鎼滅储璧勬枡"
        /></label>
      </div>
    </div>
    <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
    <div class="document-surface">
      <div class="document-surface__heading">
        <span>璧勬枡鍒楄〃</span><small>{{ filteredItems.length }} 涓粨鏋?/small>
      </div>
      <div v-if="isLoading" class="loading-state">姝ｅ湪鍔犺浇璧勬枡...</div>
      <div v-else-if="!filteredItems.length" class="empty-state">
        <FolderOpen :size="24" /><strong>娌℃湁鍖归厤鐨勮祫鏂?/strong
        ><span>鎹竴涓叧閿瘝鎴栬祫鏂欏垎绫昏瘯璇曘€?/span>
      </div>
      <div v-else class="document-table" role="table" aria-label="鐭ヨ瘑搴撹祫鏂?>
        <div class="document-table__header" role="row">
          <span>璧勬枡鍚嶇О</span><span>鍒嗙被</span><span>鐘舵€?/span><span>鏇存柊鏃堕棿</span
          ><span aria-label="鎿嶄綔" />
        </div>
        <article v-for="item in filteredItems" :key="item.id" class="document-row" role="row">
          <div class="document-name" role="cell">
            <span class="file-icon" :class="`file-icon--${item.file_type.toLowerCase()}`"
              ><FileText
                v-if="item.file_type === 'MD' || item.file_type === 'TXT'"
                :size="18" /><FileArchive v-else :size="18" /></span
            ><span class="document-name__text"
              ><strong>{{ item.filename }}</strong
              ><small>{{ item.summary }}</small></span
            >
          </div>
          <span class="document-category" role="cell">{{ item.category }}</span
          ><span role="cell" class="status-badge" :class="`status-badge--${item.status}`"
            ><i />{{ statusCopy(item.status) }}</span
          ><span class="document-date" role="cell"
            >{{ formatDate(item.created_at)
            }}<small
              >{{ formatSize(item.size_bytes)
              }}{{ item.chunk_count ? ` 路 ${item.chunk_count} 涓墖娈礰 : "" }}</small
            ></span
          >
          <div class="document-actions" role="cell">
            <button class="row-menu" title="鏇村鎿嶄綔" aria-label="鏇村鎿嶄綔">
              <MoreHorizontal :size="18" /></button
            ><button
              class="row-delete"
              title="鍒犻櫎璧勬枡"
              aria-label="鍒犻櫎璧勬枡"
              @click="removeDocument(item.id)"
            >
              <Trash2 :size="16" />
            </button>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.knowledge-page {
  max-width: 1420px;
  margin: 0 auto;
  padding: 42px clamp(22px, 4vw, 62px) 56px;
}
.page-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
}
.breadcrumb {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 15px;
  color: #89938e;
  font-size: 12px;
}
.breadcrumb strong {
  color: #59635e;
  font-weight: 600;
}
.page-heading h1 {
  margin: 0;
  color: var(--ink);
  font-size: 30px;
  font-weight: 730;
  line-height: 1.08;
}
.page-heading p {
  max-width: 570px;
  margin: 10px 0 0;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.65;
}
.upload-button {
  display: inline-flex;
  height: 40px;
  align-items: center;
  gap: 8px;
  border: 0;
  border-radius: 7px;
  padding: 0 14px;
  color: white;
  background: #245c49;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
}
.upload-button:hover {
  background: #174d3b;
}
.upload-button input {
  display: none;
}
.workspace-summary {
  display: flex;
  min-height: 74px;
  align-items: center;
  gap: 12px;
  margin-top: 34px;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}
.summary-card {
  display: flex;
  min-width: 152px;
  align-items: center;
  gap: 10px;
  padding-right: 22px;
  border-right: 1px solid var(--line);
}
.summary-card__icon {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border-radius: 7px;
  color: #365f95;
  background: #e8f0fa;
}
.summary-card__icon--green {
  color: #287451;
  background: #e5f3ea;
}
.summary-card span:not(.summary-card__icon) {
  display: block;
  color: #8c9691;
  font-size: 11px;
}
.summary-card strong {
  display: block;
  margin-top: 2px;
  color: var(--ink);
  font-size: 16px;
  line-height: 1;
}
.workspace-summary__note {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-left: auto;
  color: #75817a;
  font-size: 12px;
}
.live-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #49a878;
}
.knowledge-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-top: 28px;
}
.filter-tabs {
  display: flex;
  gap: 3px;
  padding: 3px;
  border-radius: 8px;
  background: #e9ede8;
}
.filter-tabs button {
  height: 30px;
  border: 0;
  border-radius: 5px;
  padding: 0 10px;
  color: #68736d;
  background: transparent;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.filter-tabs .filter-tab--active {
  color: #1d2923;
  background: white;
  box-shadow: 0 1px 2px rgba(20, 39, 28, 0.1);
}
.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.category-select {
  display: flex;
  height: 34px;
  align-items: center;
  gap: 5px;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 0 8px 0 10px;
  color: #8c9690;
  background: white;
  font-size: 11px;
}
.category-select select {
  appearance: none;
  min-width: 62px;
  border: 0;
  outline: 0;
  color: #4e5a53;
  background: transparent;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}
.category-select svg {
  pointer-events: none;
}
.document-search {
  display: flex;
  width: 180px;
  height: 34px;
  align-items: center;
  gap: 7px;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 0 9px;
  color: #89938e;
  background: white;
}
.document-search:focus-within {
  border-color: #92c9ae;
  box-shadow: 0 0 0 3px rgba(67, 138, 109, 0.1);
}
.document-search input {
  width: 100%;
  border: 0;
  outline: 0;
  color: var(--ink);
  background: transparent;
  font-size: 12px;
}
.error-message {
  margin: 18px 0 0;
  border: 1px solid #f3d2ca;
  border-radius: 7px;
  padding: 10px 12px;
  color: #a3412a;
  background: #fff6f3;
  font-size: 13px;
}
.document-surface {
  margin-top: 14px;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
}
.document-surface__heading {
  display: flex;
  height: 52px;
  align-items: center;
  gap: 9px;
  border-bottom: 1px solid var(--line);
  padding: 0 18px;
  color: var(--ink);
  font-size: 13px;
  font-weight: 700;
}
.document-surface__heading small {
  color: #97a09b;
  font-size: 11px;
  font-weight: 500;
}
.document-table__header,
.document-row {
  display: grid;
  grid-template-columns:
    minmax(260px, 1.55fr) minmax(90px, 0.55fr) minmax(85px, 0.48fr) minmax(142px, 0.7fr)
    76px;
  align-items: center;
  column-gap: 18px;
  padding: 0 18px;
}
.document-table__header {
  height: 37px;
  border-bottom: 1px solid #edf0ed;
  color: #96a09a;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.document-row {
  min-height: 78px;
  border-bottom: 1px solid #edf0ed;
}
.document-row:last-child {
  border-bottom: 0;
}
.document-row:hover {
  background: #fbfcfa;
}
.document-name {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 11px;
}
.file-icon {
  display: grid;
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  place-items: center;
  border-radius: 6px;
  color: #3b6d9e;
  background: #eaf1f9;
}
.file-icon--csv {
  color: #277352;
  background: #e6f4eb;
}
.file-icon--pdf {
  color: #ae5044;
  background: #f9eae7;
}
.file-icon--docx {
  color: #406ea6;
  background: #e7effa;
}
.document-name__text {
  min-width: 0;
}
.document-name strong {
  display: block;
  overflow: hidden;
  color: #27332c;
  font-size: 13px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.document-name small {
  display: block;
  overflow: hidden;
  margin-top: 4px;
  color: #88938d;
  font-size: 11px;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.document-category {
  color: #65716a;
  font-size: 12px;
}
.status-badge {
  display: inline-flex;
  width: max-content;
  align-items: center;
  gap: 6px;
  border-radius: 99px;
  padding: 4px 7px;
  font-size: 11px;
  font-weight: 650;
}
.status-badge i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
}
.status-badge--indexed {
  color: #277352;
  background: #e8f5ec;
}
.status-badge--uploading,
.status-badge--parsing {
  color: #90631d;
  background: #fbf2dc;
}
.status-badge--failed {
  color: #b44837;
  background: #f9e9e5;
}
.document-date {
  color: #65716a;
  font-size: 12px;
}
.document-date small {
  display: block;
  margin-top: 3px;
  color: #a0a9a4;
  font-size: 10px;
}
.document-actions {
  display: flex;
  justify-content: flex-end;
  gap: 2px;
}
.row-menu,
.row-delete {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border: 0;
  border-radius: 5px;
  color: #8b9690;
  background: transparent;
  cursor: pointer;
  opacity: 0.65;
}
.document-row:hover .row-menu,
.document-row:hover .row-delete {
  opacity: 1;
}
.row-delete:hover {
  color: #b44332;
  background: #f9e9e5;
}
.loading-state,
.empty-state {
  display: grid;
  min-height: 220px;
  place-content: center;
  justify-items: center;
  color: #89948e;
  font-size: 13px;
}
.empty-state svg {
  margin-bottom: 10px;
  color: #a0afa5;
}
.empty-state strong {
  color: #59645e;
  font-size: 13px;
}
.empty-state span {
  margin-top: 5px;
  font-size: 12px;
}
@media (max-width: 860px) {
  .knowledge-page {
    padding-top: 30px;
  }
  .knowledge-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }
  .toolbar-actions {
    width: 100%;
    justify-content: space-between;
  }
  .document-table {
    overflow-x: auto;
  }
  .document-table__header,
  .document-row {
    min-width: 770px;
  }
}
@media (max-width: 560px) {
  .knowledge-page {
    padding-inline: 16px;
  }
  .page-heading {
    align-items: flex-start;
    flex-direction: column;
  }
  .page-heading h1 {
    font-size: 27px;
  }
  .upload-button {
    width: 100%;
    justify-content: center;
  }
  .summary-card {
    min-width: 0;
    flex: 1;
    padding-right: 10px;
  }
  .workspace-summary__note {
    display: none;
  }
  .filter-tabs {
    width: 100%;
    overflow-x: auto;
  }
  .filter-tabs button {
    flex: 0 0 auto;
  }
  .document-search {
    width: 158px;
  }
}
</style>

