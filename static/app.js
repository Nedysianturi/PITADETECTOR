// Pita Detector - Interactive Frontend Application Logic

document.addEventListener("DOMContentLoaded", () => {
    // Elements
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");
    const btnBrowse = document.getElementById("btnBrowse");
    const loadingSection = document.getElementById("loadingSection");
    const resultsSection = document.getElementById("resultsSection");
    const sampleButtons = document.querySelectorAll(".btn-sample");

    // Verdict Elements
    const verdictIcon = document.getElementById("verdictIcon");
    const verdictHeading = document.getElementById("verdictHeading");
    const verdictSummary = document.getElementById("verdictSummary");
    const confidenceBadge = document.getElementById("confidenceBadge");
    
    // Probability Bars
    const valAi = document.getElementById("valAi");
    const barAi = document.getElementById("barAi");
    const valPhone = document.getElementById("valPhone");
    const barPhone = document.getElementById("barPhone");
    const valCamera = document.getElementById("valCamera");
    const barCamera = document.getElementById("barCamera");
    const valWebcam = document.getElementById("valWebcam");
    const barWebcam = document.getElementById("barWebcam");

    // Viewport Elements
    const mainDisplayImg = document.getElementById("mainDisplayImg");
    const viewportBadge = document.getElementById("viewportBadge");
    const viewportCaption = document.getElementById("viewportCaption");
    const modeButtons = document.querySelectorAll(".mode-btn");

    // Detail Containers
    const reasonsContainer = document.getElementById("reasonsContainer");
    const exifGrid = document.getElementById("exifGrid");
    const exifStatusBadge = document.getElementById("exifStatusBadge");
    const metricsTableBody = document.getElementById("metricsTableBody");

    // Live Camera Elements
    const btnOpenCamera = document.getElementById("btnOpenCamera");
    const cameraModal = document.getElementById("cameraModal");
    const btnCloseCamera = document.getElementById("btnCloseCamera");
    const btnCancelCamera = document.getElementById("btnCancelCamera");
    const btnSnapPhoto = document.getElementById("btnSnapPhoto");
    const cameraVideo = document.getElementById("cameraVideo");
    const cameraResTag = document.getElementById("cameraResTag");
    const cameraDeviceSelect = document.getElementById("cameraDeviceSelect");
    const snapshotCanvas = document.getElementById("snapshotCanvas");

    // State
    let currentAnalysisData = null;
    let currentVisualMode = "original";
    let activeMediaStream = null;

    // -------------------------------------------------------------
    // WEBRTC LIVE CAMERA LOGIC
    // -------------------------------------------------------------
    async function startCamera(deviceId = null) {
        stopCameraStream();
        cameraModal.style.display = "flex";
        cameraResTag.textContent = "Menghubungkan ke kamera...";

        const constraints = {
            video: deviceId 
                ? { deviceId: { exact: deviceId } }
                : { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" }
        };

        try {
            activeMediaStream = await navigator.mediaDevices.getUserMedia(constraints);
            cameraVideo.srcObject = activeMediaStream;

            cameraVideo.onloadedmetadata = () => {
                cameraResTag.textContent = `${cameraVideo.videoWidth} x ${cameraVideo.videoHeight} px • Aktif`;
            };

            await populateCameraDevices();
        } catch (err) {
            console.error("Camera access error:", err);
            cameraResTag.textContent = "Gagal mengakses kamera";
            alert("Tidak dapat mengakses kamera. Pastikan izin kamera telah diberikan pada browser.");
            stopCameraStream();
        }
    }

    async function populateCameraDevices() {
        try {
            if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
            const devices = await navigator.mediaDevices.enumerateDevices();
            const videoDevices = devices.filter(d => d.kind === "videoinput");
            
            cameraDeviceSelect.innerHTML = "";
            videoDevices.forEach((dev, idx) => {
                const opt = document.createElement("option");
                opt.value = dev.deviceId;
                opt.textContent = dev.label || `Kamera ${idx + 1}`;
                cameraDeviceSelect.appendChild(opt);
            });

            cameraDeviceSelect.style.display = videoDevices.length > 1 ? "block" : "none";
        } catch (e) {
            console.warn("Device enumeration failed:", e);
        }
    }

    function stopCameraStream() {
        if (activeMediaStream) {
            activeMediaStream.getTracks().forEach(track => track.stop());
            activeMediaStream = null;
        }
        if (cameraVideo) {
            cameraVideo.srcObject = null;
        }
        cameraModal.style.display = "none";
    }

    if (btnOpenCamera) {
        btnOpenCamera.addEventListener("click", () => startCamera());
    }
    if (btnCloseCamera) {
        btnCloseCamera.addEventListener("click", stopCameraStream);
    }
    if (btnCancelCamera) {
        btnCancelCamera.addEventListener("click", stopCameraStream);
    }
    if (cameraDeviceSelect) {
        cameraDeviceSelect.addEventListener("change", () => {
            if (cameraDeviceSelect.value) startCamera(cameraDeviceSelect.value);
        });
    }

    if (btnSnapPhoto) {
        btnSnapPhoto.addEventListener("click", () => {
            if (!cameraVideo.videoWidth || !cameraVideo.videoHeight) {
                alert("Kamera belum siap atau tidak aktif.");
                return;
            }

            snapshotCanvas.width = cameraVideo.videoWidth;
            snapshotCanvas.height = cameraVideo.videoHeight;
            const ctx = snapshotCanvas.getContext("2d");
            ctx.drawImage(cameraVideo, 0, 0, snapshotCanvas.width, snapshotCanvas.height);

            stopCameraStream();

            snapshotCanvas.toBlob((blob) => {
                if (!blob) {
                    alert("Gagal memproses jepretan kamera.");
                    return;
                }
                const file = new File([blob], "live_webcam_capture.jpg", { type: "image/jpeg" });
                handleFileUpload(file);
            }, "image/jpeg", 0.92);
        });
    }

    // -------------------------------------------------------------
    // EVENT LISTENERS: Upload & Drag & Drop
    // -------------------------------------------------------------
    btnBrowse.addEventListener("click", (e) => {
        e.stopPropagation();
        fileInput.click();
    });

    dropZone.addEventListener("click", () => {
        fileInput.click();
    });

    fileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files[0]) {
            handleFileUpload(e.target.files[0]);
        }
    });

    ["dragenter", "dragover"].forEach(evt => {
        dropZone.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add("drag-over");
        });
    });

    ["dragleave", "drop"].forEach(evt => {
        dropZone.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove("drag-over");
        });
    });

    dropZone.addEventListener("drop", (e) => {
        const dt = e.dataTransfer;
        if (dt.files && dt.files[0]) {
            handleFileUpload(dt.files[0]);
        }
    });

    // Support Ctrl+V paste from clipboard anywhere on the page
    window.addEventListener("paste", (e) => {
        const items = (e.clipboardData || e.originalEvent.clipboardData).items;
        for (let item of items) {
            if (item.kind === "file" && item.type.startsWith("image/")) {
                const blob = item.getAsFile();
                handleFileUpload(blob);
                break;
            }
        }
    });

    // -------------------------------------------------------------
    // QUICK SAMPLE BUTTONS
    // -------------------------------------------------------------
    sampleButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const sampleId = btn.getAttribute("data-sample");
            handleSampleRequest(sampleId);
        });
    });

    // -------------------------------------------------------------
    // VISUAL MODE SWITCHER
    // -------------------------------------------------------------
    modeButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            modeButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentVisualMode = btn.getAttribute("data-mode");
            updateVisualMode();
        });
    });

    // -------------------------------------------------------------
    // API CALLS
    // -------------------------------------------------------------
    async function handleFileUpload(file) {
        if (!file.type.startsWith("image/")) {
            alert("Harap pilih berkas gambar yang valid (JPEG, PNG, WEBP, dll.)");
            return;
        }

        showLoading(true);
        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch("/api/analyze", {
                method: "POST",
                body: formData
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Gagal menganalisis gambar.");
            }

            const data = await res.json();
            renderAnalysis(data);
        } catch (error) {
            alert(`Terjadi kesalahan: ${error.message}`);
        } finally {
            showLoading(false);
        }
    }

    async function handleSampleRequest(sampleId) {
        showLoading(true);
        try {
            const res = await fetch(`/api/sample/${sampleId}`);
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Gagal memuat sampel.");
            }
            const data = await res.json();
            renderAnalysis(data);
        } catch (error) {
            alert(`Terjadi kesalahan memuat sampel: ${error.message}`);
        } finally {
            showLoading(false);
        }
    }

    function showLoading(isLoading) {
        if (isLoading) {
            loadingSection.style.display = "block";
            resultsSection.style.display = "none";
            loadingSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
        } else {
            loadingSection.style.display = "none";
        }
    }

    // -------------------------------------------------------------
    // RENDER ANALYSIS RESULTS
    // -------------------------------------------------------------
    function renderAnalysis(data) {
        currentAnalysisData = data;
        const cls = data.classification;

        // 1. Verdict & Confidence
        verdictIcon.textContent = cls.verdict_icon || "🔍";
        verdictHeading.textContent = cls.verdict_label;
        
        confidenceBadge.textContent = `Keyakinan: ${cls.confidence}`;
        confidenceBadge.className = "badge-confidence";
        if (cls.confidence === "Sedang") confidenceBadge.classList.add("medium");
        if (cls.confidence === "Rendah") confidenceBadge.classList.add("low");

        // Set summary
        if (cls.verdict === "ai") {
            verdictSummary.textContent = "Gambar memiliki karakteristik kuat hasil generasi kecerdasan buatan (Latent Diffusion / GAN) atau jejak metadata prompt.";
        } else if (cls.verdict === "smartphone") {
            verdictSummary.textContent = "Gambar teridentifikasi dari kamera smartphone dengan jejak komputasi penajaman (ISP) dan karakteristik sensor kecil.";
        } else if (cls.verdict === "webcam") {
            verdictSummary.textContent = "Gambar teridentifikasi dari kamera laptop / webcam dengan format video call, optik fixed-focus lembut, dan noise sensor indoor.";
        } else {
            verdictSummary.textContent = "Gambar teridentifikasi dari kamera dedicated (DSLR / Mirrorless) dengan optik fisik murni dan noise sensor alami.";
        }

        // 2. Probabilities
        const pAi = cls.probabilities.ai || 0;
        const pPhone = cls.probabilities.smartphone || 0;
        const pCamera = cls.probabilities.dedicated_camera || 0;
        const pWebcam = cls.probabilities.webcam || 0;

        valAi.textContent = `${pAi}%`;
        valPhone.textContent = `${pPhone}%`;
        valCamera.textContent = `${pCamera}%`;
        if (valWebcam) valWebcam.textContent = `${pWebcam}%`;

        setTimeout(() => {
            barAi.style.width = `${pAi}%`;
            barPhone.style.width = `${pPhone}%`;
            barCamera.style.width = `${pCamera}%`;
            if (barWebcam) barWebcam.style.width = `${pWebcam}%`;
        }, 50);

        // 3. Reset & Render Visual Mode
        currentVisualMode = "original";
        modeButtons.forEach(b => {
            b.classList.toggle("active", b.getAttribute("data-mode") === "original");
        });
        updateVisualMode();

        // 4. Reasons List
        reasonsContainer.innerHTML = "";
        if (cls.reasons && cls.reasons.length > 0) {
            cls.reasons.forEach(reason => {
                const item = document.createElement("div");
                item.className = "reason-item";
                // parse bold markdown **text**
                const formatted = reason.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                item.innerHTML = `
                    <span class="reason-icon">🔹</span>
                    <span>${formatted}</span>
                `;
                reasonsContainer.appendChild(item);
            });
        } else {
            reasonsContainer.innerHTML = `<div class="reason-item">Tidak ada anomali signifikan yang terdeteksi.</div>`;
        }

        // 5. EXIF Grid
        const meta = data.metadata;
        exifGrid.innerHTML = "";
        
        if (meta.has_exif) {
            exifStatusBadge.textContent = "EXIF Terdeteksi";
            exifStatusBadge.style.color = "var(--accent-emerald)";
            exifStatusBadge.style.borderColor = "rgba(16, 185, 129, 0.4)";
        } else {
            exifStatusBadge.textContent = "EXIF Dihapus / Kosong";
            exifStatusBadge.style.color = "var(--accent-amber)";
            exifStatusBadge.style.borderColor = "rgba(245, 158, 11, 0.4)";
        }

        const exifFields = [
            { label: "Merek Kamera / Device", val: meta.make || "Tidak tercatat" },
            { label: "Model Perangkat", val: meta.model || "Tidak tercatat" },
            { label: "Model Lensa", val: meta.lens_model || "Standar / Internal" },
            { label: "Focal Length Fisik", val: meta.focal_length ? `${meta.focal_length} mm` : "N/A" },
            { label: "Focal Length (35mm Eq)", val: meta.focal_length_35mm ? `${meta.focal_length_35mm} mm` : "N/A" },
            { label: "Aperture / Diafragma", val: meta.f_number ? `f/${meta.f_number}` : "N/A" },
            { label: "ISO Speed", val: meta.iso ? `${meta.iso}` : "N/A" },
            { label: "Dimensi Gambar", val: data.dimensions }
        ];

        exifFields.forEach(f => {
            const div = document.createElement("div");
            div.className = "exif-item";
            div.innerHTML = `
                <div class="exif-key">${f.label}</div>
                <div class="exif-val">${f.val}</div>
            `;
            exifGrid.appendChild(div);
        });

        // 6. Metrics Table
        renderMetricsTable(data);

        // Show Results Section
        resultsSection.style.display = "block";
        resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    // -------------------------------------------------------------
    // VISUAL MODE SWITCHING
    // -------------------------------------------------------------
    function updateVisualMode() {
        if (!currentAnalysisData) return;
        const d = currentAnalysisData;

        switch (currentVisualMode) {
            case "original":
                mainDisplayImg.src = d.original_thumb_b64;
                viewportBadge.textContent = "Foto Asli";
                viewportCaption.textContent = `Menampilkan foto asli (${d.filename}, ${d.dimensions}, format ${d.format}).`;
                break;
            case "ela":
                mainDisplayImg.src = d.ela.ela_image_b64;
                viewportBadge.textContent = "Error Level Analysis (ELA)";
                viewportCaption.textContent = `Peta selisih kompresi JPEG diferensial (Mean Error: ${d.ela.mean_error}). Area berpendar terang menandakan area frekuensi tinggi atau rekayasa multi-kompresi.`;
                break;
            case "fft":
                mainDisplayImg.src = d.frequency.fft_image_b64;
                viewportBadge.textContent = "2D FFT Power Spectrum";
                viewportCaption.textContent = `Sidik jari frekuensi 2D Fourier. Model AI difusi/GAN sering menunjukkan kisi periodik simetris atau roll-off cutoff VAE, sedangkan sensor optik memiliki peluruhan radial kontinu.`;
                break;
            case "noise":
                mainDisplayImg.src = d.noise.noise_image_b64;
                viewportBadge.textContent = "Noise Residual Sensor";
                viewportCaption.textContent = `Peta noise frekuensi tinggi (Standar Deviasi: ${d.noise.avg_noise_std}). Sensor kamera nyata memiliki butiran noise fisik, sedangkan HP menampilkan halo penajaman komputasi tepi objek.`;
                break;
        }
    }

    // -------------------------------------------------------------
    // METRICS TABLE
    // -------------------------------------------------------------
    function renderMetricsTable(data) {
        metricsTableBody.innerHTML = "";

        const metrics = [
            {
                param: "Standar Deviasi Noise",
                val: `${data.noise.avg_noise_std}`,
                indic: data.noise.avg_noise_std < 2.5 ? "Ketiadaan noise (Indikasi AI)" : (data.noise.avg_noise_std >= 4.0 ? "Noise alami sensor kamera" : "Noise komputasi moderat")
            },
            {
                param: "Rasio Halo Penajaman (ISP)",
                val: `${data.noise.halo_ratio}`,
                indic: data.noise.halo_ratio > 36.0 ? "Digital Sharpening kuat (Khas HP)" : "Transisi optik murni (Khas DSLR)"
            },
            {
                param: "Mean Error ELA",
                val: `${data.ela.mean_error}`,
                indic: data.ela.mean_error < 2.0 ? "Kompresi sangat halus / Sintetik" : "Variasi kompresi foto normal"
            },
            {
                param: "Kurtosis Frekuensi Tinggi 2D FFT",
                val: `${data.frequency.hf_kurtosis}`,
                indic: data.frequency.hf_kurtosis > 4.5 ? "Lonjakan frekuensi diskrit (Indikasi AI)" : "Spektrum kontinu alami (Optik Sensor)"
            },
            {
                param: "Rasio Energi Frekuensi Tinggi",
                val: `${(data.frequency.high_energy_ratio * 100).toFixed(1)}%`,
                indic: data.frequency.high_energy_ratio < 0.05 ? "Kehalusan mikro buatan (Smoothing AI)" : "Kaya detail sensorik optik"
            }
        ];

        metrics.forEach(m => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${m.param}</strong></td>
                <td class="font-mono">${m.val}</td>
                <td>${m.indic}</td>
            `;
            metricsTableBody.appendChild(tr);
        });
    }
});
