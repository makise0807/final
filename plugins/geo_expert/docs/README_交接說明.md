# Geo-Orchestrator — 交接手冊

> **版本**：v2.0（2026-05）｜**接收團隊**：AI2k7yj3m06  
> **系統摘要**：整合衛星遙測（OpenEO）、向量圖資（PostGIS）與法規語意搜尋（ChromaDB RAG）的智慧型都市計畫空間分析平台。  
> 支援 **Streamlit 網頁介面** 與 **CLI 多輪 AI Agent** 兩種操作模式。

---

## 目錄

1. [系統架構概覽](#1-系統架構概覽)
2. [環境需求](#2-環境需求)
3. [快速啟動（5步驟）](#3-快速啟動5步驟)
4. [目錄結構說明](#4-目錄結構說明)
5. [核心模組說明](#5-核心模組說明)
6. [AI Agent 使用指南](#6-ai-agent-使用指南)
7. [Embedding 模式說明](#7-embedding-模式說明)
8. [資料庫維護](#8-資料庫維護)
9. [常見問題排查](#9-常見問題排查)
10. [封裝打包](#10-封裝打包)

---

## 1. 系統架構概覽

```
使用者（瀏覽器 / CLI）
       │
       ├─ Streamlit (app.py)         ← 網頁 UI，4 個功能頁籤
       └─ agent_chat.py              ← CLI 多輪對話 Agent
              │
   ┌──────────┼──────────────────────┐
   │          │                      │
analysis/  analysis/           analysis/
eo_tools   spatial_tools       rag_tools
(OpenEO)   (PostGIS/SQLAlchemy)(ChromaDB)
   │          │                      │
Taiwan     PostgreSQL 15       ChromaDB
GeoDataCube + PostGIS 3.4      (Docker)
(遠端 API)  (Docker)
```

**三大引擎：**

| 引擎 | 模組 | 功能 |
|------|------|------|
| 🛰️ 地球觀測 | `analysis/eo_tools.py` | NDVI、地表覆蓋分類、雲遮、超解析度、崩塌偵測、時序變遷 |
| 🗺️ 向量空間 | `analysis/spatial_tools.py` | 緩衝、鄰近、疊合、合併（全走 PostGIS SQL） |
| 📚 法規 RAG | `analysis/rag_tools.py` | 語意搜尋 49 份都市計畫法規（ChromaDB + bge-m3） |

---

## 2. 環境需求

| 項目 | 最低需求 |
|------|---------|
| OS | Windows 10 / macOS 12 / Ubuntu 22.04 |
| Python | **3.10+**（建議 3.11） |
| RAM | 8 GB（16 GB 建議，sentence-transformers 需要空間） |
| 硬碟 | 5 GB（含 Docker image、模型快取） |
| Docker Desktop | 最新版（含 Docker Compose v2） |
| 網路 | 首次安裝需下載模型約 **1.3 GB**；OpenEO 需要帳號 |

---

## 3. 快速啟動（5步驟）

### 步驟 1 — 解壓縮並進入目錄

```bash
# 解壓縮後進入專案根目錄
cd geo-orchestrator
```

### 步驟 2 — 建立環境變數

```bash
# Windows（PowerShell）
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

開啟 `.env`，填入以下必要欄位：

```ini
# 預設使用本地 Embedding，不需 API Key
EMBEDDING_PROVIDER=local

# PostGIS 資料庫密碼（需與 docker-compose 一致）
POSTGRES_PASSWORD=geopassword

# LM Studio 本地 LLM（若要使用 AI 對話）
# 留空則 AI 對話功能在 UI 顯示「離線」提示
LM_STUDIO_URL=http://localhost:1234/v1
LM_STUDIO_MODEL=local-model
```

> ⚠️ **OpenEO 遙測功能**需要填入 `OPENEO_USER` / `OPENEO_PASSWORD`（台灣 GeoDataCube 帳號）。無帳號時 EO 工具會回傳錯誤，但其他功能不受影響。

### 步驟 3 — 啟動 Docker 服務

```bash
cd database
docker compose up -d
cd ..
```

等待約 **30 秒**讓 PostGIS 完全初始化。確認服務狀態：

```bash
docker compose -f database/docker-compose.yml ps
```

三個服務應皆顯示 `running`：

| 容器名稱 | 服務 | 對外端口 |
|---------|------|---------|
| `geo_postgis` | PostgreSQL 15 + PostGIS 3.4 | `5433` |
| `geo_chromadb` | ChromaDB 向量資料庫 | `8000` |
| `geo_pgadmin` | pgAdmin 4（可選） | `5050` |

### 步驟 4 — 還原 PostGIS 圖資資料庫

```bash
# 1. 將備份檔複製進容器
docker cp database/geodb_export.dump geo_postgis:/tmp/geodb_export.dump

# 2. 執行還原（首次約需 30-60 秒）
docker exec -it geo_postgis pg_restore -U geouser -d geodb -F c /tmp/geodb_export.dump

# 3. 驗證：應顯示地籍筆數（非 0）
docker exec -it geo_postgis psql -U geouser -d geodb -c "SELECT COUNT(*) FROM cadastral_parcels;"
```

> 若出現 `already exists` 警告可忽略，資料已正確還原。若還原後查無資料，加上 `--clean` 旗標重試。

### 步驟 5 — 安裝 Python 套件並啟動

```bash
# 安裝套件（sentence-transformers 約 700 MB，需要時間）
pip install -r requirements.txt

# 首次匯入法規 Embedding（約 3-10 分鐘，視 CPU 而定）
# 會自動下載 BAAI/bge-m3 模型（~570 MB）並快取至 ~/.cache/huggingface
python database/ingest_txt_to_chroma.py

# 啟動 Streamlit 網頁介面
streamlit run app.py
```

瀏覽器開啟：**http://localhost:8501**

---

## 4. 目錄結構說明

```
geo-orchestrator/
│
├── app.py                          # Streamlit 主程式（網頁 UI）
├── agent_chat.py                   # CLI 多輪 AI Agent（終端機互動）
├── build_workflow_db.py            # 建置專家工作流程知識庫
├── test_all.py                     # 系統整合測試腳本
│
├── analysis/                       # 核心分析引擎（三大模組）
│   ├── eo_tools.py                 # 衛星遙測工具（OpenEO）
│   ├── spatial_tools.py            # 向量空間分析（PostGIS）
│   └── rag_tools.py                # 法規語意搜尋（ChromaDB）
│
├── database/
│   ├── docker-compose.yml          # Docker 服務定義（PostGIS + ChromaDB + pgAdmin）
│   ├── init_postgis.py             # 初始化 DB Schema + 圖資匯入函式
│   ├── ingest_txt_to_chroma.py     # 法規文件 Embedding 匯入腳本
│   └── geodb_export.dump           # PostGIS 完整圖資備份（56 MB）
│
├── data/
│   ├── regulations/                # 49 份都市計畫法規文件（.txt / .md）
│   ├── workflow_db/
│   │   └── expert_workflows.json  # 10 個預定義 AI 工作流程情境
│   ├── eo_outputs/                 # OpenEO 下載的 GeoTIFF 輸出
│   ├── analysis_results/           # 本地分析結果（VARI、K-Means、變遷圖）
│   ├── styles/                     # 上傳的 QML 樣式檔
│   └── dummy_parcels.geojson       # 測試用假地塊資料
│
├── scripts/
│   ├── init_demo_data.py           # 匯入展示用空間資料
│   ├── list_docs.py                # 列出 ChromaDB 已匯入文件
│   ├── view_chroma.py              # 查看 ChromaDB collection 內容
│   ├── test_local_ndvi.py          # 本地 NDVI 功能測試
│   └── test_local_tiff.py          # 本地 GeoTIFF 讀取測試
│
├── .env.example                    # 環境變數範本
├── .env                            # 實際環境變數（請勿 commit）
├── requirements.txt                # Python 套件清單
└── .gitignore
```

---

## 5. 核心模組說明

### 5.1 `analysis/eo_tools.py` — 衛星遙測引擎

連接台灣 GeoDataCube（OpenEO 標準），提供 **9 個分析工具**：

| 函式 | 功能 | 需要 OpenEO？ |
|------|------|:---:|
| `calculate_ndvi()` | Sentinel-2 NDVI 植生指數計算 | ✅ |
| `classify_landcover()` | AI 地表覆蓋分類（建物/植被/水體） | ✅ |
| `detect_cloudmask()` | 雲遮遮罩偵測 | ✅ |
| `process_superresolution()` | 超解析度影像增強 | ✅ |
| `detect_landslide()` | 崩塌偵測（災前/災後比對） | ✅ |
| `calculate_local_vari()` | **本地** RGB 影像 VARI 植被指數 | ❌ |
| `detect_local_change()` | **本地** 時序 VARI 變遷偵測 | ❌ |
| `extract_local_water_features()` | **本地** 水體指數萃取 | ❌ |
| `classify_local_kmeans()` | **本地** K-Means 無監督分類 | ❌ |
| `generate_openeo_bbox()` | 依中心點座標動態生成 BBox | ❌ |

> **本地工具**（後四者）讀取 `data/eo_outputs/Mataan_TimeSeries/` 內的 GeoTIFF，無需 OpenEO 帳號，可直接在離線環境使用。

### 5.2 `analysis/spatial_tools.py` — 向量空間引擎

透過 SQLAlchemy + PostGIS SQL 執行，提供 **4 個 GIS 工具**：

| 函式 | 功能 | PostGIS 操作 |
|------|------|-------------|
| `analyze_buffer()` | 緩衝區分析（正/負值） | `ST_Buffer` |
| `analyze_proximity()` | 鄰近設施查詢（KNN） | `ST_DWithin` + `ST_Distance` |
| `calculate_overlay_intersection()` | 疊合交集（覆蓋率計算） | `ST_Intersection` |
| `analyze_dissolve_union()` | 多地號合併 | `ST_Union` |

**資料表白名單**（`target_table` 可用值）：
- `cadastral_parcels` — 地籍圖
- `conservation_zones` — 保育區
- `legal_buildings` — 合法建物

### 5.3 `analysis/rag_tools.py` — 法規語意搜尋

```python
from analysis.rag_tools import search_regulations

# 一般語意搜尋
result = search_regulations("山坡地開發裁罰", top_k=5)

# 指定法規來源過濾
result = search_regulations("容積率", source_filter="都市計畫法", top_k=3)
```

ChromaDB 中已匯入 **49 份法規文件**，涵蓋都市計畫法、國土計畫法、水土保持法、都市更新條例等。

---

## 6. AI Agent 使用指南

### 6.1 Streamlit 網頁 AI 介面（Tab 3：🤖 AI 助理）

1. 啟動 **LM Studio** → 載入模型（建議 Llama 3.2 或 Gemma 3）→ 點 `Local Server` → `Start Server`
2. 確認 LM Studio 運行於 `http://localhost:1234`
3. 重新整理 Streamlit 頁面，側邊欄 `🤖 LM Studio` 應顯示 `Online`
4. 在 Tab 3 的對話框輸入任務

### 6.2 CLI Agent（`agent_chat.py`）

```bash
python agent_chat.py
```

**CLI 特殊指令：**

| 指令 | 功能 |
|------|------|
| `/clear` | 清除對話記憶，重新開始 |
| `/history` | 顯示目前對話記憶摘要 |
| `/tools` | 列出所有可用工具及描述 |
| `exit` | 離開程式 |

**對話範例：**

```
👤 您: 幫我檢查馬太鞍農地，比較 2025-08 和 2025-11 的植被變化
🤖 Antigravity 思考中…
   🔧 呼叫工具：detect_local_change
   📋 參數：{"tiff_before": "2025-08", "tiff_after": "2025-11"}
   ✅ 結果：{"status": "success", "stats": {"vegetation_loss_pct": 12.3, ...}}
🤖 Antigravity: 分析完成！該區域在此期間植被減少 12.3%...
```

### 6.3 預定義工作流程（10 個情境）

位於 `data/workflow_db/expert_workflows.json`，已涵蓋：

| ID | 情境 |
|----|------|
| WF-001 | 農業區違章工廠盤查 |
| WF-002 | 山坡地保育區超限利用監測 |
| WF-003 | 都市更新單元劃定條件評估 |
| WF-004 | 河川行水區違法傾倒廢棄物監測 |
| WF-005 | 農地種電合法性稽查 |
| WF-006 | 新訂都市計畫區位適宜性分析 |
| WF-007 | 變更特定農業區為一般農業區檢核 |
| WF-008 | 捷運場站周邊 TOD 容積獎勵試算 |
| WF-009 | 崩塌地與淹塞湖防災潛勢評估 |
| WF-010 | 國土綠網與生態敏感區開發干擾評估 |

---

## 7. Embedding 模式說明

在 `.env` 中設定 `EMBEDDING_PROVIDER`：

| 模式 | 設定值 | 需要 API | 下載大小 | 說明 |
|------|--------|:-------:|---------|------|
| **本地模型（推薦）** | `local` | ❌ | ~570 MB | `BAAI/bge-m3`，支援繁中，首次自動下載 |
| Google Gemini | `google` | ✅ | — | 免費但有每日配額，需 `GOOGLE_API_KEY` |
| OpenAI | `openai` | ✅ | — | 需要有餘額，需 `OPENAI_API_KEY` |

**更換本地模型**（省空間、較低準確度）：

```ini
LOCAL_EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
```

更換模型後，需重新執行 `python database/ingest_txt_to_chroma.py` 重建 ChromaDB。

---

## 8. 資料庫維護

### 8.1 匯入新空間資料

**方式 A：透過 Streamlit UI 上傳**（支援 GeoJSON / SHP ZIP / KML / 7z）  
→ 進入 Tab 2「🗂️ 圖資管理」→「📥 圖資匯入」

**方式 B：Python 腳本**

```python
from database.init_postgis import import_geojson, get_engine
engine = get_engine()
rows = import_geojson(filepath="your_data.geojson", engine=engine, source="描述來源")
print(f"匯入 {rows} 筆")
```

### 8.2 備份 PostGIS

```bash
docker exec geo_postgis pg_dump -U geouser -d geodb -F c -f /tmp/backup.dump
docker cp geo_postgis:/tmp/backup.dump ./database/geodb_export_$(date +%Y%m%d).dump
```

### 8.3 新增法規文件至 ChromaDB

1. 將新法規 `.txt` 檔放入 `data/regulations/`
2. 執行：`python database/ingest_txt_to_chroma.py`
3. 腳本會自動略過已匯入的文件（依 `source` metadata 去重）

### 8.4 查看 ChromaDB 狀態

```bash
python scripts/list_docs.py     # 列出所有已匯入文件
python scripts/view_chroma.py   # 查看 collection 詳細內容
```

---

## 9. 常見問題排查

**Q: `docker compose up -d` 後 PostGIS 無法連線**  
A: 等待 30 秒後再試。執行 `docker logs geo_postgis` 查看啟動日誌，確認出現 `database system is ready to accept connections`。

**Q: pg_restore 後 `cadastral_parcels` 查不到資料**  
A: 加上 `--clean` 旗標：
```bash
docker exec -it geo_postgis pg_restore -U geouser -d geodb -F c --clean /tmp/geodb_export.dump
```

**Q: ChromaDB 連線失敗（port 8000）**  
A: 確認容器已啟動：`docker ps | grep chromadb`。若 8000 端口被佔用，在 `.env` 修改 `CHROMA_PORT`，並同步更新 `docker-compose.yml`。

**Q: `BAAI/bge-m3` 下載失敗（無網路環境）**  
A: 改用小模型：`.env` 設定 `LOCAL_EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2`，再重新 ingest。

**Q: LM Studio 顯示 Online 但 AI 對話沒有呼叫工具**  
A: 確認載入的模型支援 function calling（推薦 Llama 3.2、Hermes 3、Mistral Nemo）。Gemma 系列不支援 tools 參數，Agent 會自動退回純文字模式。

**Q: `sentence-transformers` 安裝失敗**  
A: 確認 Python 版本 >= 3.10。若在 Windows 遇到 C++ 編譯問題，先安裝：
```
pip install --upgrade wheel setuptools
```

**Q: OpenEO 工具回傳 `EnvironmentError`**  
A: `.env` 中的 `OPENEO_USER` / `OPENEO_PASSWORD` 未設定或填入預設值。向台灣 GeoDataCube（colife.org.tw）申請帳號，或直接使用本地分析工具（`calculate_local_vari`、`detect_local_change` 等）。

**Q: Streamlit 啟動後 `ModuleNotFoundError`**  
A: 確認在專案根目錄（`geo-orchestrator/`）下執行 `streamlit run app.py`，勿在子目錄下執行。

---

## 10. 封裝打包

執行以下腳本即可產生可交接的 ZIP 壓縮檔（已排除 `.env`、`__pycache__`、`.venv`）：

```bash
python package_for_transfer.py
```

腳本會建立 `geo-orchestrator_transfer_YYYYMMDD.zip`，包含：
- 全部原始碼
- `database/geodb_export.dump`（PostGIS 圖資備份）
- `data/regulations/`（49 份法規）
- `data/workflow_db/`（工作流程知識庫）
- `.env.example`（環境變數範本）
- 本手冊

> **注意**：`data/eo_outputs/` 資料夾（GeoTIFF 影像）體積較大（視分析次數而定），預設**排除**於打包範圍。若需要一併移交，請手動複製。

---

## 附錄：服務 Port 速查

| 服務 | URL / 連線字串 |
|------|--------------|
| Streamlit UI | http://localhost:8501 |
| LM Studio API | http://localhost:1234/v1 |
| ChromaDB API | http://localhost:8000 |
| PostgreSQL | `postgresql://geouser:密碼@localhost:5433/geodb` |
| pgAdmin 4 | http://localhost:5050（帳號見 `.env`） |

---

*本手冊由 Antigravity AI 自動生成，最後更新：2026-05*
