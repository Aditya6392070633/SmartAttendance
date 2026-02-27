import { useState, useEffect, useRef } from "react";

const API = "https://smartattendancebackend-2dja.onrender.com";

const ScanLine = () => (
  <div style={{
    position: "absolute", top: 0, left: 0, right: 0, height: "2px",
    background: "linear-gradient(90deg, transparent, #00ff88, transparent)",
    animation: "scanline 2.5s linear infinite",
    boxShadow: "0 0 12px #00ff88"
  }} />
);

const FaceGrid = ({ active, detected, scanning }) => {
  const corners = ["top-left", "top-right", "bottom-left", "bottom-right"];
  const cornerStyles = {
    "top-left": { top: 0, left: 0, borderTop: "3px solid #00ff88", borderLeft: "3px solid #00ff88" },
    "top-right": { top: 0, right: 0, borderTop: "3px solid #00ff88", borderRight: "3px solid #00ff88" },
    "bottom-left": { bottom: 0, left: 0, borderBottom: "3px solid #00ff88", borderLeft: "3px solid #00ff88" },
    "bottom-right": { bottom: 0, right: 0, borderBottom: "3px solid #00ff88", borderRight: "3px solid #00ff88" },
  };

  return (
    <div style={{
      position: "absolute", top: "50%", left: "50%",
      transform: "translate(-50%, -50%)",
      width: "160px", height: "190px",
      opacity: active ? 1 : 0.3,
      transition: "all 0.4s ease",
      zIndex: 2
    }}>
      {corners.map(c => (
        <div key={c} style={{
          position: "absolute", width: "24px", height: "24px", ...cornerStyles[c],
          boxShadow: detected ? "0 0 8px #00ff88" : "none"
        }} />
      ))}
      {detected && (
        <>
          <div style={{
            position: "absolute", top: "50%", left: 0, right: 0, height: "1px",
            background: "rgba(0,255,136,0.3)", transform: "translateY(-50%)"
          }} />
          <div style={{
            position: "absolute", left: "50%", top: 0, bottom: 0, width: "1px",
            background: "rgba(0,255,136,0.3)", transform: "translateX(-50%)"
          }} />
          <div style={{
            position: "absolute", top: "50%", left: "50%",
            transform: "translate(-50%,-50%)",
            width: "60px", height: "60px",
            border: "1px solid rgba(0,255,136,0.4)",
            borderRadius: "50%"
          }} />
        </>
      )}
    </div>
  );
};

export default function SmartAttendance() {
  const [students_, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [detected, setDetected] = useState(false);
  const [currentScan, setCurrentScan] = useState(null);
  const [scanResult, setScanResult] = useState(null);
  const [activeTab, setActiveTab] = useState("scan");
  const [dots, setDots] = useState("");
  const [liveTime, setLiveTime] = useState(new Date());
  const [feedNoise, setFeedNoise] = useState(0);
  const [cameraError, setCameraError] = useState(null);
  const [cameraReady, setCameraReady] = useState(false);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  // ✅ Start webcam
  const startCamera = async () => {
    try {
      setCameraError(null);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: "user" }
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setCameraReady(true);
      }
    } catch (err) {
      console.error("Camera error:", err);
      setCameraError("Camera access denied or not available");
      setCameraReady(false);
    }
  };

  // ✅ Stop webcam
  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
      setCameraReady(false);
    }
  };

  // ✅ Capture photo and send to backend
  const captureAndScan = async () => {
    if (scanning) return;
    if (!cameraReady || !videoRef.current) {
      alert("Camera not ready. Please allow camera access.");
      return;
    }

    setScanning(true);
    setDetected(false);
    setScanResult(null);
    setCurrentScan(null);

    setTimeout(() => setDetected(true), 800);

    try {
      const canvas = canvasRef.current;
      const video = videoRef.current;
      canvas.width = 640;
      canvas.height = 480;
      canvas.getContext("2d").drawImage(video, 0, 0, 640, 480);

      const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/jpeg", 0.9));
      const formData = new FormData();
      formData.append("face_image", blob, "scan.jpg");

      const res = await fetch(`${API}/attendance/scan`, {
        method: "POST",
        body: formData
      });

      const data = await res.json();

      if (res.ok && data.student) {
        setScanResult({ type: "success", student: { name: data.student, roll: data.roll } });
        setStudents(prev => prev.map(s =>
          s.roll === data.roll
            ? { ...s, status: "present", time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) }
            : s
        ));
        await fetchTodayAttendance();
      } else {
        setScanResult({ type: "error", message: data.detail || "Face not recognized" });
      }
    } catch (err) {
      console.error("Scan error:", err);
      setScanResult({ type: "error", message: "Scan failed. Check backend connection." });
    } finally {
      setScanning(false);
      setTimeout(() => setDetected(false), 2000);
    }
  };

  // ✅ Fetch real students from backend
  const fetchStudents = async () => {
    try {
      const res = await fetch(`${API}/students/`);
      const data = await res.json();
      const mapped = data.map(s => ({
        id: s.id,
        name: s.name,
        roll: s.roll,
        dept: s.department,
        avatar: s.name.split(" ").map(n => n[0]).join("").toUpperCase(),
        status: null,
        time: null
      }));
      setStudents(mapped);
    } catch (err) {
      console.error("Failed to fetch students:", err);
    } finally {
      setLoading(false);
    }
  };

  // ✅ Fetch today's attendance and merge with students
  const fetchTodayAttendance = async () => {
    try {
      const res = await fetch(`${API}/attendance/today`);
      const data = await res.json();
      setStudents(prev => prev.map(s => {
        const record = data.find(a => a.student_id === s.id);
        if (record) {
          return {
            ...s,
            status: record.status,
            time: record.marked_at
              ? new Date(record.marked_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
              : "--:--"
          };
        }
        return s;
      }));
    } catch (err) {
      console.error("Failed to fetch attendance:", err);
    }
  };

  useEffect(() => {
    fetchStudents().then(() => fetchTodayAttendance());
    startCamera();
    return () => stopCamera();
  }, []);

  useEffect(() => {
    const t = setInterval(() => setLiveTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    if (scanning) {
      const t = setInterval(() => setDots(d => d.length >= 3 ? "" : d + "."), 400);
      return () => clearInterval(t);
    }
  }, [scanning]);

  useEffect(() => {
    const t = setInterval(() => setFeedNoise(Math.random()), 200);
    return () => clearInterval(t);
  }, []);

  // ✅ Mark absent via API
  const markAbsent = async (id) => {
    try {
      await fetch(`${API}/attendance/mark-absent/${id}`, { method: "POST" });
      setStudents(prev => prev.map(s =>
        s.id === id ? { ...s, status: "absent", time: "--:--" } : s
      ));
    } catch (err) {
      console.error("Failed to mark absent:", err);
    }
  };

  // ✅ Reset — reload from API
  const reset = async () => {
    setScanResult(null);
    setCurrentScan(null);
    setScanning(false);
    setDetected(false);
    setLoading(true);
    await fetchStudents();
    await fetchTodayAttendance();
  };

  const present = students_.filter(s => s.status === "present").length;
  const absent = students_.filter(s => s.status === "absent").length;
  const unmarked = students_.filter(s => s.status === null).length;
  const pct = students_.length > 0 ? Math.round((present / students_.length) * 100) : 0;

  return (
    <div style={{
      minHeight: "100vh",
      background: "#080c10",
      fontFamily: "'Courier New', monospace",
      color: "#c8d8c0",
      padding: "0",
      overflow: "hidden"
    }}>
      <style>{`
        @keyframes scanline { 0% { top: 0% } 100% { top: 100% } }
        @keyframes pulse { 0%,100% { opacity:1 } 50% { opacity:0.4 } }
        @keyframes blink { 0%,100% { opacity:1 } 49% { opacity:1 } 50% { opacity:0 } 51% { opacity:0 } }
        @keyframes fadeIn { from { opacity:0; transform:translateY(8px) } to { opacity:1; transform:translateY(0) } }
        @keyframes pop { 0% { transform:scale(0.8); opacity:0 } 60% { transform:scale(1.05) } 100% { transform:scale(1); opacity:1 } }
        @keyframes scanPulse { 0%,100% { box-shadow: 0 0 20px rgba(0,255,136,0.2) } 50% { box-shadow: 0 0 40px rgba(0,255,136,0.5) } }
        @keyframes spin { 0% { transform: rotate(0deg) } 100% { transform: rotate(360deg) } }
        .tab-btn { background: transparent; border: none; cursor: pointer; font-family: 'Courier New', monospace; font-size: 11px; letter-spacing: 2px; padding: 10px 20px; transition: all 0.2s; }
        .row-hover:hover { background: rgba(0,255,136,0.05) !important; }
        .action-btn:hover { background: rgba(0,255,136,0.15) !important; }
      `}</style>

      {/* Header */}
      <div style={{
        borderBottom: "1px solid rgba(0,255,136,0.15)",
        padding: "16px 32px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        background: "rgba(0,255,136,0.02)"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div style={{
            width: "10px", height: "10px", borderRadius: "50%",
            background: "#00ff88",
            boxShadow: "0 0 10px #00ff88",
            animation: "pulse 2s ease-in-out infinite"
          }} />
          <span style={{ fontSize: "13px", letterSpacing: "4px", color: "#00ff88", fontWeight: "bold" }}>
            FACETRACK
          </span>
          <span style={{ fontSize: "10px", letterSpacing: "2px", color: "rgba(200,216,192,0.4)" }}>
            v2.4.1
          </span>
        </div>
        <div style={{ fontSize: "11px", letterSpacing: "2px", color: "rgba(200,216,192,0.5)" }}>
          {liveTime.toLocaleDateString([], { weekday: "short", day: "2-digit", month: "short" }).toUpperCase()}
          {"  "}
          <span style={{ color: "#00ff88", animation: "blink 1s step-end infinite" }}>
            {liveTime.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
          </span>
        </div>
      </div>

      <div style={{ display: "flex", height: "calc(100vh - 57px)" }}>
        {/* Left Panel */}
        <div style={{
          width: "380px",
          borderRight: "1px solid rgba(0,255,136,0.1)",
          display: "flex",
          flexDirection: "column",
          flexShrink: 0
        }}>
          {/* Camera Feed */}
          <div style={{
            position: "relative",
            aspectRatio: "4/3",
            background: "#050809",
            borderBottom: "1px solid rgba(0,255,136,0.1)",
            overflow: "hidden"
          }}>
            {/* Grid overlay */}
            <div style={{
              position: "absolute", inset: 0,
              backgroundImage: `radial-gradient(ellipse at ${30 + feedNoise * 40}% ${30 + feedNoise * 40}%, rgba(0,255,136,0.03) 0%, transparent 60%)`,
              transition: "background 0.2s",
              zIndex: 1, pointerEvents: "none"
            }} />
            {[...Array(5)].map((_, i) => (
              <div key={i} style={{
                position: "absolute", top: 0, bottom: 0,
                left: `${(i + 1) * 16.66}%`,
                width: "1px",
                background: "rgba(0,255,136,0.04)",
                zIndex: 1, pointerEvents: "none"
              }} />
            ))}
            {[...Array(4)].map((_, i) => (
              <div key={i} style={{
                position: "absolute", left: 0, right: 0,
                top: `${(i + 1) * 20}%`,
                height: "1px",
                background: "rgba(0,255,136,0.04)",
                zIndex: 1, pointerEvents: "none"
              }} />
            ))}

            {/* Real webcam video */}
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              style={{
                position: "absolute", inset: 0,
                width: "100%", height: "100%",
                objectFit: "cover",
                opacity: cameraReady ? 0.85 : 0,
                transform: "scaleX(-1)",
                zIndex: 0
              }}
            />

            {/* Hidden canvas for capture */}
            <canvas ref={canvasRef} style={{ display: "none" }} />

            {/* Camera error */}
            {cameraError && (
              <div style={{
                position: "absolute", inset: 0, zIndex: 2,
                display: "flex", alignItems: "center", justifyContent: "center",
                flexDirection: "column", gap: "8px"
              }}>
                <span style={{ fontSize: "10px", color: "#ff6666", letterSpacing: "1px", textAlign: "center", padding: "0 16px" }}>
                  ⚠ {cameraError}
                </span>
                <button onClick={startCamera} style={{
                  background: "rgba(0,255,136,0.1)", border: "1px solid rgba(0,255,136,0.3)",
                  color: "#00ff88", fontSize: "9px", letterSpacing: "2px", padding: "6px 12px",
                  cursor: "pointer", fontFamily: "'Courier New', monospace"
                }}>
                  RETRY CAMERA
                </button>
              </div>
            )}

            {scanning && <ScanLine />}
            <FaceGrid active={scanning || detected} detected={detected} scanning={scanning} />

            <div style={{
              position: "absolute", bottom: "10px", left: "10px", right: "10px",
              display: "flex", justifyContent: "space-between", alignItems: "flex-end",
              zIndex: 3
            }}>
              <div style={{
                fontSize: "9px", letterSpacing: "2px",
                color: scanning ? "#00ff88" : cameraReady ? "rgba(0,255,136,0.6)" : "rgba(200,216,192,0.3)"
              }}>
                {scanning ? `SCANNING${dots}` : detected ? "FACE LOCKED" : cameraReady ? "CAMERA LIVE" : "NO CAMERA"}
              </div>
              <div style={{ fontSize: "9px", letterSpacing: "1px", color: "rgba(200,216,192,0.25)" }}>
                {cameraReady ? "REC ●" : "OFFLINE"} {Math.floor(feedNoise * 900 + 100)}ms
              </div>
            </div>

            {scanResult?.type === "success" && (
              <div style={{
                position: "absolute", top: "10px", left: "10px", right: "10px",
                background: "rgba(0,255,136,0.1)",
                border: "1px solid rgba(0,255,136,0.4)",
                padding: "8px 12px", fontSize: "11px", letterSpacing: "1px",
                animation: "pop 0.3s ease-out", color: "#00ff88", zIndex: 4
              }}>
                ✓ MATCH: {scanResult.student.name.toUpperCase()}
              </div>
            )}
            {scanResult?.type === "error" && (
              <div style={{
                position: "absolute", top: "10px", left: "10px", right: "10px",
                background: "rgba(255,68,68,0.1)",
                border: "1px solid rgba(255,68,68,0.4)",
                padding: "8px 12px", fontSize: "11px", letterSpacing: "1px",
                animation: "pop 0.3s ease-out", color: "#ff6666", zIndex: 4
              }}>
                ✗ {scanResult.message?.toUpperCase()}
              </div>
            )}
          </div>

          {/* Scan Button */}
          <div style={{ padding: "24px", flexShrink: 0 }}>
            <button
              onClick={captureAndScan}
              disabled={scanning || loading}
              style={{
                width: "100%", padding: "16px",
                background: scanning ? "rgba(0,255,136,0.05)" : "rgba(0,255,136,0.08)",
                border: `1px solid ${scanning ? "rgba(0,255,136,0.3)" : "rgba(0,255,136,0.5)"}`,
                color: scanning ? "rgba(0,255,136,0.5)" : "#00ff88",
                fontSize: "12px", letterSpacing: "4px",
                cursor: scanning ? "not-allowed" : "pointer",
                fontFamily: "'Courier New', monospace",
                transition: "all 0.2s",
                animation: scanning ? "scanPulse 1.5s ease-in-out infinite" : "none"
              }}
            >
              {scanning ? `SCANNING${dots}` : "▶  SCAN FACE"}
            </button>
          </div>

          {/* Stats */}
          <div style={{ margin: "0 24px 24px", display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px" }}>
            {[
              { label: "PRESENT", val: present, color: "#00ff88" },
              { label: "ABSENT", val: absent, color: "#ff4444" },
              { label: "UNMARKED", val: unmarked, color: "rgba(200,216,192,0.5)" },
            ].map(s => (
              <div key={s.label} style={{
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(255,255,255,0.06)",
                padding: "12px 8px", textAlign: "center"
              }}>
                <div style={{ fontSize: "22px", fontWeight: "bold", color: s.color, lineHeight: 1 }}>{s.val}</div>
                <div style={{ fontSize: "8px", letterSpacing: "1.5px", color: "rgba(200,216,192,0.4)", marginTop: "4px" }}>{s.label}</div>
              </div>
            ))}
          </div>

          {/* Progress */}
          <div style={{ margin: "0 24px 24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
              <span style={{ fontSize: "9px", letterSpacing: "2px", color: "rgba(200,216,192,0.4)" }}>ATTENDANCE RATE</span>
              <span style={{ fontSize: "11px", color: "#00ff88" }}>{pct}%</span>
            </div>
            <div style={{ height: "3px", background: "rgba(255,255,255,0.06)", position: "relative" }}>
              <div style={{
                height: "100%", width: `${pct}%`,
                background: "linear-gradient(90deg, #00ff88, #00cc6a)",
                transition: "width 0.6s ease",
                boxShadow: "0 0 6px #00ff88"
              }} />
            </div>
          </div>

          <div style={{ padding: "0 24px", marginTop: "auto", paddingBottom: "16px" }}>
            <button onClick={reset} className="action-btn" style={{
              width: "100%", padding: "10px",
              background: "transparent",
              border: "1px solid rgba(200,216,192,0.15)",
              color: "rgba(200,216,192,0.5)",
              fontSize: "10px", letterSpacing: "3px",
              cursor: "pointer", fontFamily: "'Courier New', monospace", transition: "all 0.2s"
            }}>
              ↺  RESET SESSION
            </button>
          </div>
        </div>

        {/* Right Panel */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{
            borderBottom: "1px solid rgba(0,255,136,0.1)",
            display: "flex", padding: "0 16px",
            background: "rgba(0,255,136,0.01)"
          }}>
            {[{ key: "scan", label: "ATTENDANCE" }, { key: "log", label: "ACTIVITY LOG" }].map(t => (
              <button key={t.key} className="tab-btn" onClick={() => setActiveTab(t.key)} style={{
                color: activeTab === t.key ? "#00ff88" : "rgba(200,216,192,0.35)",
                borderBottom: activeTab === t.key ? "2px solid #00ff88" : "2px solid transparent",
                marginBottom: "-1px"
              }}>
                {t.label}
              </button>
            ))}
          </div>

          {activeTab === "scan" && (
            <div style={{ flex: 1, overflow: "auto" }}>
              <div style={{
                display: "grid",
                gridTemplateColumns: "48px 1fr 100px 80px 90px 80px",
                padding: "12px 24px",
                borderBottom: "1px solid rgba(0,255,136,0.08)",
                fontSize: "9px", letterSpacing: "2px",
                color: "rgba(200,216,192,0.35)"
              }}>
                <span>#</span><span>STUDENT</span><span>ROLL NO.</span>
                <span>TIME</span><span>STATUS</span><span>ACTION</span>
              </div>

              {loading ? (
                <div style={{ padding: "40px", textAlign: "center", color: "rgba(0,255,136,0.4)", fontSize: "11px", letterSpacing: "2px" }}>
                  <div style={{ width: "20px", height: "20px", border: "2px solid rgba(0,255,136,0.3)", borderTop: "2px solid #00ff88", borderRadius: "50%", animation: "spin 1s linear infinite", margin: "0 auto 12px" }} />
                  LOADING STUDENTS...
                </div>
              ) : students_.length === 0 ? (
                <div style={{ padding: "40px", textAlign: "center", color: "rgba(200,216,192,0.2)", fontSize: "11px", letterSpacing: "2px" }}>
                  NO STUDENTS REGISTERED YET<br />
                  <span style={{ fontSize: "9px", marginTop: "8px", display: "block" }}>Go to {API}/docs to register students</span>
                </div>
              ) : (
                students_.map((s, i) => (
                  <div key={s.id} className="row-hover" style={{
                    display: "grid",
                    gridTemplateColumns: "48px 1fr 100px 80px 90px 80px",
                    padding: "14px 24px",
                    borderBottom: "1px solid rgba(255,255,255,0.03)",
                    alignItems: "center", transition: "all 0.2s",
                    background: currentScan?.id === s.id ? "rgba(0,255,136,0.06)" : "transparent"
                  }}>
                    <span style={{ fontSize: "11px", color: "rgba(200,216,192,0.25)" }}>{String(i + 1).padStart(2, "0")}</span>
                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                      <div style={{
                        width: "32px", height: "32px", borderRadius: "50%",
                        background: s.status === "present" ? "rgba(0,255,136,0.12)" : s.status === "absent" ? "rgba(255,68,68,0.12)" : "rgba(255,255,255,0.05)",
                        border: `1px solid ${s.status === "present" ? "rgba(0,255,136,0.4)" : s.status === "absent" ? "rgba(255,68,68,0.4)" : "rgba(255,255,255,0.1)"}`,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: "10px", fontWeight: "bold",
                        color: s.status === "present" ? "#00ff88" : s.status === "absent" ? "#ff6666" : "rgba(200,216,192,0.5)",
                        flexShrink: 0
                      }}>
                        {s.avatar}
                      </div>
                      <div>
                        <div style={{ fontSize: "12px", color: s.status ? "#c8d8c0" : "rgba(200,216,192,0.7)" }}>{s.name}</div>
                        <div style={{ fontSize: "9px", color: "rgba(200,216,192,0.3)", letterSpacing: "1px", marginTop: "1px" }}>{s.dept}</div>
                      </div>
                    </div>
                    <span style={{ fontSize: "10px", color: "rgba(200,216,192,0.4)", letterSpacing: "1px" }}>{s.roll}</span>
                    <span style={{ fontSize: "11px", color: s.time ? "#c8d8c0" : "rgba(200,216,192,0.2)" }}>{s.time || "—"}</span>
                    <div>
                      {s.status === null ? (
                        <span style={{ fontSize: "9px", letterSpacing: "1px", color: "rgba(200,216,192,0.25)" }}>PENDING</span>
                      ) : s.status === "present" ? (
                        <span style={{ fontSize: "9px", letterSpacing: "1px", color: "#00ff88", background: "rgba(0,255,136,0.08)", padding: "3px 8px", border: "1px solid rgba(0,255,136,0.2)" }}>PRESENT</span>
                      ) : (
                        <span style={{ fontSize: "9px", letterSpacing: "1px", color: "#ff6666", background: "rgba(255,68,68,0.08)", padding: "3px 8px", border: "1px solid rgba(255,68,68,0.2)" }}>ABSENT</span>
                      )}
                    </div>
                    <div>
                      {s.status === null && (
                        <button onClick={() => markAbsent(s.id)} className="action-btn" style={{
                          background: "transparent", border: "1px solid rgba(255,68,68,0.3)",
                          color: "rgba(255,100,100,0.6)", fontSize: "9px", letterSpacing: "1px",
                          padding: "4px 8px", cursor: "pointer",
                          fontFamily: "'Courier New', monospace", transition: "all 0.2s"
                        }}>ABSENT</button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === "log" && (
            <div style={{ flex: 1, overflow: "auto", padding: "24px" }}>
              <div style={{ fontSize: "10px", letterSpacing: "2px", color: "rgba(200,216,192,0.3)", marginBottom: "16px" }}>
                ── RECOGNITION LOG ──────────────────────────────
              </div>
              {students_.filter(s => s.status !== null).length === 0 ? (
                <div style={{ color: "rgba(200,216,192,0.2)", fontSize: "11px", letterSpacing: "2px" }}>NO EVENTS RECORDED YET</div>
              ) : (
                students_.filter(s => s.status !== null).map(s => (
                  <div key={s.id} style={{ display: "flex", gap: "16px", alignItems: "flex-start", marginBottom: "12px", animation: "fadeIn 0.3s ease" }}>
                    <span style={{ color: "#00ff88", fontSize: "10px", flexShrink: 0 }}>{s.time}</span>
                    <span style={{ color: "rgba(200,216,192,0.3)", fontSize: "10px" }}>›</span>
                    <span style={{ fontSize: "11px" }}>{s.name}</span>
                    <span style={{ fontSize: "9px", letterSpacing: "1px", color: s.status === "present" ? "#00ff88" : "#ff6666", marginLeft: "auto" }}>
                      {s.status === "present" ? "FACE MATCHED" : "MARKED ABSENT"}
                    </span>
                  </div>
                ))
              )}
            </div>
          )}

          <div style={{
            borderTop: "1px solid rgba(0,255,136,0.08)",
            padding: "10px 24px", display: "flex", justifyContent: "space-between",
            fontSize: "9px", letterSpacing: "1.5px", color: "rgba(200,216,192,0.25)"
          }}>
            <span>SESSION: {new Date().toLocaleDateString()}</span>
            <span>CLASS: CS301 – DATA STRUCTURES</span>
            <span>TOTAL: {students_.length} STUDENTS</span>
          </div>
        </div>
      </div>
    </div>
  );
}