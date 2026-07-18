import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  lessonAPI,
  uploadAPI,
  transcriptionAPI,
  analysisAPI,
  transcriptAPI,
  knowledgePointAPI,
  projectAPI,
  progressAPI,
} from "../services/api";
import Breadcrumb from "../components/Breadcrumb";
import StatusBadge from "../components/StatusBadge";
import ProgressBar from "../components/ProgressBar";
import FileUploader from "../components/FileUploader";
import KnowledgePointCard from "../components/KnowledgePointCard";
import ProjectCard from "../components/ProjectCard";
import Modal from "../components/Modal";

/**
 * 课节详情页 — 音频上传 / 转录 / 知识分析
 */
export default function LessonDetailPage() {
  const { id } = useParams();
  const nav = useNavigate();
  const [lesson, setLesson] = useState(null);
  const [audioInfo, setAudioInfo] = useState(null);
  const audioRef = useRef(null);
  const lastSaveRef = useRef(0);  // 上次自动保存时间戳，用于5秒节流
  const [transcripts, setTranscripts] = useState([]);
  const [knowledgePoints, setKnowledgePoints] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 操作状态
  const [uploading, setUploading] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [showTranscripts, setShowTranscripts] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [editForm, setEditForm] = useState({ title: "", description: "" });

  // 学习模式
  const [learningMode, setLearningMode] = useState(false);
  const [currentKnowledgePointId, setCurrentKnowledgePointId] = useState(null);
  const [completedKnowledgePoints, setCompletedKnowledgePoints] = useState([]);

  // 音频播放时自动识别当前知识点
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || knowledgePoints.length === 0) return;

    // 过滤并排序有时间戳的知识点
    const timedKPs = knowledgePoints
      .filter((kp) => kp.timestamp !== null && kp.timestamp !== undefined)
      .sort((a, b) => a.timestamp - b.timestamp);

    const handleTimeUpdate = () => {
      const t = audio.currentTime;
      let activeId = null;

      for (let i = 0; i < timedKPs.length; i++) {
        const kp = timedKPs[i];
        const next = timedKPs[i + 1];
        const end = next ? next.timestamp : Infinity;

        if (t >= kp.timestamp && t < end) {
          activeId = kp.id;
          break;
        }
      }

      setCurrentKnowledgePointId(activeId);
    };

    audio.addEventListener("timeupdate", handleTimeUpdate);
    return () => audio.removeEventListener("timeupdate", handleTimeUpdate);
  }, [knowledgePoints, audioInfo?.exists]);

  // 自动保存学习进度（每5秒）
useEffect(() => {

  const bindAudio = () => {

    const audio = audioRef.current;

    if (!audio) {
      console.log("audio not ready");
      return;
    }


    const timedKPs = knowledgePoints
      .filter(
        (kp) =>
          kp.timestamp !== null &&
          kp.timestamp !== undefined
      )
      .sort(
        (a,b)=>a.timestamp-b.timestamp
      );


    const handleAutoSave = () => {

      const now = Date.now();

      if(now - lastSaveRef.current < 5000)
        return;


      lastSaveRef.current = now;


      const t = audio.currentTime;
      const duration = audio.duration;


      if(!duration)
        return;


      const completed = timedKPs
        .filter(kp => t >= kp.timestamp)
        .map(kp => kp.id);


      const percent =
        Math.min(
          Math.round(t / duration * 100),
          100
        );


      console.log("AUTO SAVE",{
        lessonId:Number(id),
        currentTime:t,
        duration,
        percent
      });


      progressAPI.save(
        Number(id),
        {
          current_time:t,
          completed_knowledge_points:completed,
          progress_percent:percent
        }
      )
      .then(()=>{
        console.log("SAVE SUCCESS");
      })
      .catch(err=>{
        console.error(
          "SAVE ERROR",
          err
        );
      });

    };


    audio.addEventListener(
      "timeupdate",
      handleAutoSave
    );


    return ()=>{
      audio.removeEventListener(
        "timeupdate",
        handleAutoSave
      );
    };

  };


  const timer=setTimeout(
    bindAudio,
    1000
  );


  return ()=>clearTimeout(timer);


},[
 knowledgePoints,
 audioInfo?.exists,
 id
]);

  // 轮询定时器
  const [pollId, setPollId] = useState(null);

  const loadLesson = useCallback(async () => {
    try {
      const data = await lessonAPI.get(Number(id));
      setLesson(data);

      // 根据 status 决定是否加载详情
      if (["completed", "analyzing", "analyzed"].includes(data.status)) {
        try {
          const ai = await uploadAPI.getInfo(Number(id));
          setAudioInfo(ai);
        } catch { /* ignore */ }
      }
      if (["completed", "analyzing", "analyzed"].includes(data.status)) {
        try {
          const t = await transcriptAPI.listByLesson(Number(id));
          setTranscripts(t);
        } catch { /* ignore */ }
      }
      if (["analyzed"].includes(data.status)) {
        try {
          const kp = await knowledgePointAPI.listByLesson(Number(id));
          setKnowledgePoints(kp);
        } catch { /* ignore */ }
        try {
          const pj = await projectAPI.listByLesson(Number(id));
          setProjects(pj);
        } catch { /* ignore */ }
      }
    } catch (err) {
      setError(err.message);
    }
  }, [id]);

  useEffect(() => {
    setLoading(true);
    loadLesson().finally(() => setLoading(false));
  }, [loadLesson]);

  // 页面加载后恢复上次学习进度
useEffect(() => {

  const restoreTimer = setTimeout(async () => {

    const audio = audioRef.current;

    if (!audio) {
      console.log("audio not ready");
      return;
    }


    try {

      const progress =
        await progressAPI.get(Number(id));


      console.log(
        "RESTORE PROGRESS",
        progress
      );


      if (
        progress &&
        progress.current_time > 0
      ) {

        audio.currentTime =
          progress.current_time;


        setCompletedKnowledgePoints(
          progress.completed_knowledge_points || []
        );


        console.log(
          "RESTORE TIME:",
          progress.current_time
        );
      }


    } catch(err){

      console.error(
        "RESTORE ERROR",
        err
      );

    }


  },1000);



  return ()=>clearTimeout(restoreTimer);


},[
 audioInfo?.exists,
 id
]);

  // 轮询机制：status 为 processing/analyzing 时自动刷新
  useEffect(() => {
    if (lesson && ["processing", "analyzing"].includes(lesson.status)) {
      const timer = setInterval(() => {
        loadLesson();
      }, 3000);
      setPollId(timer);
      return () => clearInterval(timer);
    } else {
      if (pollId) {
        clearInterval(pollId);
        setPollId(null);
      }
    }
  }, [lesson?.status]);

  // ===== 上传音频 =====
  const handleUpload = async (file) => {
    setUploading(true);
    try {
      const updated = await uploadAPI.upload(Number(id), file);
      setLesson(updated);
      const info = await uploadAPI.getInfo(Number(id));
      setAudioInfo(info);
    } catch (err) {
      alert("上传失败: " + err.message);
    } finally {
      setUploading(false);
    }
  };

  // ===== 删除音频 =====
  const handleDeleteAudio = async () => {
    if (!window.confirm("确定删除音频文件？")) return;
    try {
      const updated = await uploadAPI.delete(Number(id));
      setLesson(updated);
      setAudioInfo(null);
    } catch (err) {
      alert(err.message);
    }
  };

  // ===== 音频定位 =====
  const handleSeekAudio = async (timestamp) => {
    if (!audioRef.current) return;

    audioRef.current.currentTime = timestamp;

    try {
      await audioRef.current.play();
      console.log("开始播放:", timestamp);
    } catch (err) {
      console.error("播放失败:", err);
    }
  };

  // ===== 开始学习 =====
  const handleStartLearning = async () => {
    // 找到第一个有时间戳的知识点
    const firstKP = knowledgePoints.find(
      (kp) => kp.timestamp !== null && kp.timestamp !== undefined
    );
    if (!firstKP || !audioRef.current) return;

    setLearningMode(true);

    audioRef.current.currentTime = firstKP.timestamp;
    try {
      await audioRef.current.play();
    } catch (err) {
      console.error("自动播放失败:", err);
    }
  };

  // ===== 触发转录 =====
  const handleTranscribe = async () => {
    setTranscribing(true);
    try {
      const updated = await transcriptionAPI.start(Number(id));
      setLesson(updated);
    } catch (err) {
      alert("转录失败: " + err.message);
    } finally {
      setTranscribing(false);
    }
  };

  // ===== 触发分析 =====
  const handleAnalyze = async () => {
    setAnalyzing(true);
    try {
      const updated = await analysisAPI.start(Number(id));
      setLesson(updated);
    } catch (err) {
      alert("分析失败: " + err.message);
    } finally {
      setAnalyzing(false);
    }
  };

  // ===== 编辑课节 =====
  const openEdit = () => {
    setEditForm({
      title: lesson?.title || "",
      description: lesson?.description || "",
    });
    setShowEditForm(true);
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    try {
      const updated = await lessonAPI.update(Number(id), editForm);
      setLesson(updated);
      setShowEditForm(false);
    } catch (err) {
      alert(err.message);
    }
  };

  // ===== 状态判断 =====
  const canUpload = ["pending", "uploaded"].includes(lesson?.status);
  const canTranscribe = lesson?.status === "uploaded";
  const canAnalyze =
    lesson?.status === "completed" ||
    lesson?.status === "analyzed";
  const isBusy = ["processing", "analyzing"].includes(lesson?.status);

  if (loading) return <div className="loading">加载中...</div>;
  if (error) return <div className="error">加载失败: {error}</div>;
  if (!lesson) return <div className="error">课节不存在</div>;

  return (
    <div className="page">
      <Breadcrumb items={[{ label: "课程列表", to: "/" }, { label: "课节详情" }]} />

      {/* 课节信息 + 进度条 */}
      <div className="page-header">
        <div>
          <h1>{lesson.title}</h1>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 6 }}>
            <StatusBadge status={lesson.status} />
            {isBusy && <span style={{ fontSize: "0.8rem", color: "#ff9500" }}>自动刷新中...</span>}
          </div>
        </div>
        <button className="btn btn-secondary" onClick={openEdit}>
          编辑
        </button>
      </div>

      <ProgressBar status={lesson.status} />

      {/* === 音频区域 === */}
      <section className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: "1rem", marginBottom: 12 }}>音频文件</h3>
        {canUpload && (
          <FileUploader onUpload={handleUpload} uploading={uploading} />
        )}

        {audioInfo?.exists && (
          <>
            <div
              style={{
                marginTop: 8,
                fontSize: "0.85rem",
                color:"#666"
              }}
            >
              已上传: {audioInfo.file_name}
              · {((audioInfo.file_size / 1024 / 1024).toFixed(1))}MB
            </div>

            <audio
              ref={audioRef}
              controls
              style={{
                width:"100%",
                marginTop:12
              }}
            >
              <source
                src={`http://127.0.0.1:8000/uploads/${audioInfo.file_path}`}
                type="audio/wav"
              />
            </audio>

          </>
        )}

        {lesson.audio_path && (
          <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
            <button
              className="btn btn-success btn-sm"
              onClick={handleTranscribe}
              disabled={!canTranscribe || transcribing}
            >
              {transcribing
                ? "触发中..."
                : lesson.status === "processing"
                  ? "转录中..."
                  : "触发转写"}
            </button>
            {canUpload && (
              <button
                className="btn btn-danger btn-sm"
                onClick={handleDeleteAudio}
              >
                删除音频
              </button>
            )}
          </div>
        )}
      </section>

      {/* === 转录结果区域 === */}
      {["completed", "analyzing", "analyzed"].includes(lesson.status) && (
        <section className="card" style={{ marginBottom: 16 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              cursor: "pointer",
            }}
            onClick={() => setShowTranscripts(!showTranscripts)}
          >
            <h3 style={{ fontSize: "1rem" }}>
              转录结果 ({lesson.transcript_count} 条)
            </h3>
            <span style={{ fontSize: "0.8rem", color: "#999" }}>
              {showTranscripts ? "收起 ▴" : "展开 ▾"}
            </span>
          </div>

          {showTranscripts && (
            <div
              style={{
                marginTop: 12,
                maxHeight: 300,
                overflowY: "auto",
                background: "#fafafa",
                borderRadius: 8,
                padding: 12,
                fontSize: "0.85rem",
                lineHeight: 1.8,
                color: "#555",
              }}
            >
              {transcripts.length === 0 ? (
                <p style={{ color: "#aaa", textAlign: "center" }}>
                  正在加载转写文本...
                </p>
              ) : (
                transcripts.map((seg) => {
                  const min = Math.floor(seg.start_time / 60);
                  const sec = Math.floor(seg.start_time % 60);
                  const ts = `[${String(min).padStart(2, "0")}:${String(sec).padStart(2, "0")}]`;
                  return (
                    <div key={seg.id} style={{ marginBottom: 4 }}>
                      <span style={{ color: "#667eea", fontWeight: 600, marginRight: 8 }}>
                        {ts}
                      </span>
                      {seg.text}
                    </div>
                  );
                })
              )}
            </div>
          )}

          <div style={{ marginTop: 12 }}>
            <button
              className="btn btn-primary btn-sm"
              onClick={handleAnalyze}
              disabled={!canAnalyze || analyzing}
            >
              {analyzing
                ? "触发中..."
                : lesson.status === "analyzing"
                  ? "分析中..."
                  : lesson.status === "analyzed"
                    ? "重新AI分析"
                    : "触发AI分析"}
            </button>
          </div>
        </section>
      )}

      {/* === 知识点区域 === */}
      {lesson.status === "analyzed" && lesson.knowledge_point_count > 0 && (
        <section style={{ marginBottom: 16 }}>
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 12,
          }}>
            <h3 style={{ fontSize: "1rem", margin: 0 }}>
              知识点 ({lesson.knowledge_point_count})
            </h3>
            {audioInfo?.exists && knowledgePoints.some(
              (kp) => kp.timestamp !== null && kp.timestamp !== undefined
            ) && (
              <button
                className="btn btn-success"
                onClick={handleStartLearning}
              >
                {learningMode ? "学习中..." : "▶ 开始学习"}
              </button>
            )}
          </div>
          {knowledgePoints.length === 0 ? (
            <p style={{ color: "#aaa", fontSize: "0.85rem" }}>
              知识图谱已生成（共 {lesson.knowledge_point_count} 条）
            </p>
          ) : (
            knowledgePoints.map((kp) => (
              <KnowledgePointCard
                key={kp.id}
                point={kp}
                onSeek={handleSeekAudio}
                isActive={kp.id === currentKnowledgePointId}
              />
            ))
          )}
        </section>
      )}

      {/* === 项目区域 === */}
      {lesson.status === "analyzed" && lesson.project_count > 0 && (
        <section style={{ marginBottom: 16 }}>
          <h3 style={{ fontSize: "1rem", marginBottom: 12 }}>
            项目实战 ({lesson.project_count})
          </h3>
          {projects.length === 0 ? (
            <p style={{ color: "#aaa", fontSize: "0.85rem" }}>
              项目分析已生成（共 {lesson.project_count} 条）
            </p>
          ) : (
            projects.map((pj) => <ProjectCard key={pj.id} project={pj} />)
          )}
        </section>
      )}

      {/* 编辑弹窗 */}
      <Modal
        open={showEditForm}
        onClose={() => setShowEditForm(false)}
        title="编辑课节"
      >
        <form onSubmit={handleEditSubmit}>
          <div className="form-group">
            <label>课节标题 *</label>
            <input
              className="form-input"
              value={editForm.title}
              onChange={(e) =>
                setEditForm({ ...editForm, title: e.target.value })
              }
              autoFocus
            />
          </div>
          <div className="form-group">
            <label>课节描述</label>
            <textarea
              className="form-input"
              rows={3}
              value={editForm.description}
              onChange={(e) =>
                setEditForm({ ...editForm, description: e.target.value })
              }
            />
          </div>
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setShowEditForm(false)}
            >
              取消
            </button>
            <button type="submit" className="btn btn-primary">
              保存
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
