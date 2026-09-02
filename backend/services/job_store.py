"""
转换任务持久化存储模块

将每次「小说转剧本」任务的状态与结果落盘到磁盘，解决：
- 客户端断线 / 刷新页面后，后台任务继续运行且结果不丢失
- 预览页可从后端读取最近一次已完成的结果（不再只依赖 sessionStorage）
- 相同文本重新提交时可断点续跑（复用已完成分片）
- 防止重复提交（相同指纹的任务进行中时拒绝）

磁盘布局：
    <data_dir>/<job_id>/
        meta.json        任务元数据（状态/进度/错误/最近日志）
        request.json     完整请求参数（用于断点续跑）
        chunks/chunk_NNN.yaml  每个分片解析成功后的标准 YAML
        result.yaml      最终合并的完整剧本 YAML
        result.json      最终结果（script_data + yaml_text，供 API 返回）
"""

import hashlib
import json
import os
import shutil
import threading
import time
import uuid

# ============================================================
# 常量配置
# ============================================================

# 分片逻辑版本号：参与文本指纹计算。
# 分片规则（CHUNK_SIZE/CHUNK_OVERLAP 等）变更时必须 +1，否则旧分片无法与新切分对齐。
CHUNKING_VERSION = "1"

# 最大保留任务数（超出时清理最旧的已完成/失败/取消任务，running 任务永不清理）
MAX_RETAINED_JOBS = 10

# meta.json 中保留的最近日志条数上限
MAX_LOG_ENTRIES = 100

# running 任务的过期秒数：超过该时间没有任何 meta 更新视为僵死
# （正常任务每个分片都会更新 meta，92 片的大任务间隔也远小于此值）
STALE_RUNNING_SECONDS = 600

# 合法任务状态
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"


def compute_fingerprint(
    novel_text: str, model_name: str, base_url: str, chunking_version: str = CHUNKING_VERSION
) -> str:
    """
    计算转换任务的文本指纹，用于重复提交检测与断点续跑匹配。

    指纹 = sha256(chunking_version + 模型 + API地址 + 正文全文)。
    同一文本 + 同一模型重复提交会得到相同指纹；
    分片逻辑版本变更时指纹必然变化，避免旧分片错配新切分。

    Args:
        novel_text: 预处理前的原始小说正文
        model_name: 使用的模型名称
        base_url: API 地址（不同平台结果不同，纳入指纹）
        chunking_version: 分片逻辑版本号

    Returns:
        str: 64 位十六进制指纹
    """
    hasher = hashlib.sha256()
    hasher.update(chunking_version.encode("utf-8"))
    hasher.update(b"\x00")
    hasher.update(model_name.encode("utf-8"))
    hasher.update(b"\x00")
    hasher.update(base_url.encode("utf-8"))
    hasher.update(b"\x00")
    hasher.update(novel_text.encode("utf-8"))
    return hasher.hexdigest()


class JobStore:
    """
    线程安全的任务落盘存储。

    转换解析运行在后台线程，SSE 生成器与 REST 接口运行在事件循环线程，
    所有 meta.json 的读写都通过 RLock 串行化；分片/结果文件一次性写入后不再修改。
    """

    def __init__(self, data_dir: str | None = None):
        """
        Args:
            data_dir: 任务数据根目录。默认取环境变量 JOB_DATA_DIR，
                      未设置时使用 <当前工作目录>/data/jobs（容器内为 /app/data/jobs）。
        """
        self.data_dir = data_dir or os.getenv(
            "JOB_DATA_DIR", os.path.join(os.getcwd(), "data", "jobs")
        )
        self._lock = threading.RLock()
        # 已请求取消的任务集合（内存即时生效，同时持久化到 meta）
        self._cancel_requested: set[str] = set()
        os.makedirs(self.data_dir, exist_ok=True)
        self._recover_interrupted_jobs()

    # --------------------------------------------------------
    # 路径辅助
    # --------------------------------------------------------

    def _job_dir(self, job_id: str) -> str:
        return os.path.join(self.data_dir, job_id)

    def _meta_path(self, job_id: str) -> str:
        return os.path.join(self._job_dir(job_id), "meta.json")

    def _request_path(self, job_id: str) -> str:
        return os.path.join(self._job_dir(job_id), "request.json")

    def _chunks_dir(self, job_id: str) -> str:
        return os.path.join(self._job_dir(job_id), "chunks")

    def _chunk_path(self, job_id: str, index: int) -> str:
        return os.path.join(self._chunks_dir(job_id), f"chunk_{index:03d}.yaml")

    def _result_json_path(self, job_id: str) -> str:
        return os.path.join(self._job_dir(job_id), "result.json")

    def _result_yaml_path(self, job_id: str) -> str:
        return os.path.join(self._job_dir(job_id), "result.yaml")

    # --------------------------------------------------------
    # JSON 读写（原子写入）
    # --------------------------------------------------------

    @staticmethod
    def _write_json_atomic(path: str, payload) -> None:
        """先写临时文件再 os.replace，避免读到半截 JSON"""
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

    @staticmethod
    def _read_json(path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    # --------------------------------------------------------
    # 任务创建与查询
    # --------------------------------------------------------

    def create_job(
        self,
        novel_title: str,
        novel_text: str,
        novel_file_content: str | None,
        api_key: str,
        base_url: str,
        model_name: str,
        fingerprint: str,
    ) -> dict:
        """
        创建新任务：分配 job_id、写 meta.json 与 request.json、执行保留策略清理。

        Args:
            novel_title: 小说名称
            novel_text: 粘贴的正文文本（可为空，与文件二选一）
            novel_file_content: 上传文件解码后的文本内容（可为空）
            api_key/base_url/model_name: AI 配置（原样落盘用于断点续跑）
            fingerprint: compute_fingerprint 的结果

        Returns:
            dict: 初始 meta
        """
        job_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
        os.makedirs(self._chunks_dir(job_id), exist_ok=True)

        meta = {
            "job_id": job_id,
            "status": STATUS_RUNNING,
            "novel_title": novel_title,
            "fingerprint": fingerprint,
            "model_name": model_name,
            "base_url": base_url,
            "created_at": time.time(),
            "updated_at": time.time(),
            "total_chunks": 0,
            "completed_chunks": 0,
            "failed_chunks": [],
            "resumed_chunks": [],
            "error": None,
            "message": "",
            "cancel_requested": False,
            "logs": [],
        }
        request_payload = {
            "novel_title": novel_title,
            "novel_text": novel_text,
            "novel_file_content": novel_file_content or "",
            "api_key": api_key,
            "base_url": base_url,
            "model_name": model_name,
            "fingerprint": fingerprint,
        }
        with self._lock:
            self._write_json_atomic(self._meta_path(job_id), meta)
            self._write_json_atomic(self._request_path(job_id), request_payload)
            self._cleanup_old_jobs()
        return meta

    def get_job(self, job_id: str) -> dict | None:
        """读取任务 meta；不存在或 job_id 非法时返回 None"""
        if not job_id or "/" in job_id or "\\" in job_id or job_id.startswith("."):
            return None
        with self._lock:
            return self._read_json(self._meta_path(job_id))

    def list_jobs(self, limit: int = 20) -> list[dict]:
        """按创建时间倒序列出任务 meta"""
        jobs: list[dict] = []
        try:
            entries = os.listdir(self.data_dir)
        except OSError:
            return jobs
        for name in entries:
            meta = self.get_job(name)
            if meta:
                jobs.append(meta)
        jobs.sort(key=lambda m: m.get("created_at", 0), reverse=True)
        return jobs[:limit]

    def latest_job(self) -> dict | None:
        """最近创建的任务 meta（无任务时返回 None）"""
        jobs = self.list_jobs(limit=1)
        return jobs[0] if jobs else None

    def find_running_job(self, fingerprint: str) -> dict | None:
        """查找指定指纹且状态为 running 的任务（防重复提交）"""
        now = time.time()
        for meta in self.list_jobs(limit=50):
            if meta.get("fingerprint") != fingerprint or meta.get("status") != STATUS_RUNNING:
                continue
            # 僵死任务（长时间无进度更新）不算进行中，放行重新提交
            if now - meta.get("updated_at", 0) > STALE_RUNNING_SECONDS:
                continue
            return meta
        return None

    def find_resumable_job(self, fingerprint: str) -> dict | None:
        """
        查找指定指纹的最近一个可续跑任务（断点续跑来源）。

        返回 failed / cancelled / completed 状态的任务，以及
        超过僵死阈值仍处于 running 的任务（进程中断后遗留）。
        completed 任务用于「相同请求直接返回缓存结果」。
        """
        now = time.time()
        for meta in self.list_jobs(limit=50):
            if meta.get("fingerprint") != fingerprint:
                continue
            status = meta.get("status")
            if status == STATUS_RUNNING:
                # 仅僵死的 running 任务可续跑（活跃任务属于防重复范畴）
                if now - meta.get("updated_at", 0) > STALE_RUNNING_SECONDS:
                    return meta
                continue
            return meta
        return None

    def load_request(self, job_id: str) -> dict | None:
        """读取任务请求参数（用于断点续跑重建解析流程）"""
        return self._read_json(self._request_path(job_id))

    # --------------------------------------------------------
    # 状态更新
    # --------------------------------------------------------

    def update_meta(self, job_id: str, **fields) -> dict | None:
        """
        原子更新 meta 字段并刷新 updated_at。

        Args:
            job_id: 任务 ID
            **fields: 要覆盖的字段

        Returns:
            dict | None: 更新后的完整 meta；任务不存在时返回 None
        """
        with self._lock:
            meta = self._read_json(self._meta_path(job_id))
            if meta is None:
                return None
            meta.update(fields)
            if "updated_at" not in fields:
                meta["updated_at"] = time.time()
            self._write_json_atomic(self._meta_path(job_id), meta)
            return meta

    def append_log(self, job_id: str, stage: str, message: str) -> None:
        """向 meta.logs 追加一条进度日志（超过上限时丢弃最旧的）"""
        entry = {"time": time.strftime("%H:%M:%S"), "stage": stage, "message": message[:300]}
        with self._lock:
            meta = self._read_json(self._meta_path(job_id))
            if meta is None:
                return
            logs = meta.get("logs") or []
            logs.append(entry)
            meta["logs"] = logs[-MAX_LOG_ENTRIES:]
            meta["updated_at"] = time.time()
            self._write_json_atomic(self._meta_path(job_id), meta)

    # --------------------------------------------------------
    # 分片持久化（断点续跑的数据来源）
    # --------------------------------------------------------

    def set_total_chunks(self, job_id: str, total: int) -> None:
        """分片切割完成后记录总数"""
        self.update_meta(job_id, total_chunks=total)

    def save_chunk(self, job_id: str, index: int, yaml_text: str) -> None:
        """保存单个分片解析成功后的标准 YAML，并累计 completed_chunks"""
        with self._lock:
            os.makedirs(self._chunks_dir(job_id), exist_ok=True)
            tmp = self._chunk_path(job_id, index) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(yaml_text)
            os.replace(tmp, self._chunk_path(job_id, index))
            meta = self._read_json(self._meta_path(job_id))
            if meta is not None:
                meta["completed_chunks"] = len(self.list_chunk_indices(job_id))
                meta["updated_at"] = time.time()
                self._write_json_atomic(self._meta_path(job_id), meta)

    def mark_chunk_failed(self, job_id: str, index: int) -> None:
        """记录解析失败被跳过的分片序号"""
        with self._lock:
            meta = self._read_json(self._meta_path(job_id))
            if meta is None:
                return
            failed: list[int] = meta.get("failed_chunks") or []
            if index not in failed:
                failed.append(index)
                meta["failed_chunks"] = failed
                meta["updated_at"] = time.time()
                self._write_json_atomic(self._meta_path(job_id), meta)

    def mark_chunk_resumed(self, job_id: str, index: int) -> None:
        """记录本次运行复用了历史分片的序号（不计入 LLM 调用）"""
        with self._lock:
            meta = self._read_json(self._meta_path(job_id))
            if meta is None:
                return
            resumed: list[int] = meta.get("resumed_chunks") or []
            if index not in resumed:
                resumed.append(index)
                meta["resumed_chunks"] = resumed
                meta["updated_at"] = time.time()
                self._write_json_atomic(self._meta_path(job_id), meta)

    def list_chunk_indices(self, job_id: str) -> list[int]:
        """列出已落盘分片的序号（升序）"""
        try:
            names = os.listdir(self._chunks_dir(job_id))
        except OSError:
            return []
        indices = []
        for name in names:
            if name.startswith("chunk_") and name.endswith(".yaml"):
                try:
                    indices.append(int(name[6:-5]))
                except ValueError:
                    continue
        return sorted(indices)

    def get_chunk_yaml(self, job_id: str, index: int) -> str | None:
        """读取已落盘分片的 YAML 文本；不存在返回 None"""
        try:
            with open(self._chunk_path(job_id, index), "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            return None

    # --------------------------------------------------------
    # 最终结果
    # --------------------------------------------------------

    def finalize_result(self, job_id: str, result: dict, yaml_text: str) -> None:
        """
        任务完成：写入 result.json / result.yaml 并置状态为 completed。

        Args:
            job_id: 任务 ID
            result: {scenes, characters, script_data, ...} 结构（API result 事件载荷）
            yaml_text: 合并后的完整 YAML 文本
        """
        with self._lock:
            payload = dict(result)
            payload["job_id"] = job_id
            self._write_json_atomic(self._result_json_path(job_id), payload)
            with open(self._result_yaml_path(job_id), "w", encoding="utf-8") as f:
                f.write(yaml_text)
            self.update_meta(job_id, status=STATUS_COMPLETED, error=None)

    def load_result(self, job_id: str) -> dict | None:
        """读取已完成任务的 result.json；不存在或未完成返回 None"""
        meta = self.get_job(job_id)
        if not meta or meta.get("status") != STATUS_COMPLETED:
            return None
        return self._read_json(self._result_json_path(job_id))

    def mark_failed(self, job_id: str, error: str) -> None:
        """任务失败：写入错误信息并置状态为 failed"""
        self.update_meta(job_id, status=STATUS_FAILED, error=error[:500])

    def mark_cancelled(self, job_id: str) -> None:
        """任务取消：置状态为 cancelled"""
        with self._lock:
            self._cancel_requested.discard(job_id)
            self.update_meta(job_id, status=STATUS_CANCELLED)

    # --------------------------------------------------------
    # 取消（协作式：解析线程在分片间检查）
    # --------------------------------------------------------

    def request_cancel(self, job_id: str) -> bool:
        """
        请求取消任务。

        Args:
            job_id: 任务 ID

        Returns:
            bool: True 表示请求已受理（任务存在且未结束）
        """
        meta = self.get_job(job_id)
        if not meta or meta.get("status") not in (STATUS_RUNNING,):
            return False
        with self._lock:
            self._cancel_requested.add(job_id)
            self.update_meta(job_id, cancel_requested=True)
        return True

    def is_cancel_requested(self, job_id: str) -> bool:
        """解析线程在分片间调用：是否已请求取消"""
        if job_id in self._cancel_requested:
            return True
        meta = self.get_job(job_id)
        return bool(meta and meta.get("cancel_requested"))

    # --------------------------------------------------------
    # 保留策略
    # --------------------------------------------------------

    def _recover_interrupted_jobs(self) -> None:
        """
        启动时恢复中断任务：将仍处于 running 的任务标记为 failed。

        服务重启后解析线程必然已丢失，running 状态属于遗留脏数据；
        标记为 failed 后可被断点续跑拾起，已完成分片不会浪费。
        """
        for meta in self.list_jobs(limit=100):
            if meta.get("status") == STATUS_RUNNING:
                self.mark_failed(meta["job_id"], "服务重启导致任务中断（已完成分片已保留，重新提交相同文本可续跑）")

    def _cleanup_old_jobs(self) -> None:
        """任务数超过上限时清理最旧的非 running 任务（调用方需持有锁）"""
        jobs = self.list_jobs(limit=1000)
        if len(jobs) <= MAX_RETAINED_JOBS:
            return
        removable = [j for j in jobs if j.get("status") != STATUS_RUNNING]
        for meta in removable[: len(jobs) - MAX_RETAINED_JOBS]:
            shutil.rmtree(self._job_dir(meta["job_id"]), ignore_errors=True)


# ============================================================
# 模块级单例
# ============================================================

_store: JobStore | None = None
_store_lock = threading.Lock()


def get_job_store() -> JobStore:
    """获取全局 JobStore 单例（按需初始化）"""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = JobStore()
    return _store
