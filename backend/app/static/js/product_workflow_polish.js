
(function () {
    function textOf(el) {
        return (el && el.textContent || "").replace(/\s+/g, " ").trim().toLowerCase();
    }

    function findButtonByText(parts) {
        const buttons = Array.from(document.querySelectorAll("button, a.btn, input[type='submit']"));
        return buttons.find((btn) => {
            const txt = textOf(btn);
            return parts.every((part) => txt.includes(part.toLowerCase()));
        });
    }

    function safeClick(label, parts) {
        const btn = findButtonByText(parts);
        if (!btn) {
            return false;
        }

        if (btn.disabled) {
            return false;
        }

        btn.click();
        return true;
    }

    function findCardsByHeadingText(keyword) {
        const headings = Array.from(document.querySelectorAll("h1, h2, h3"));
        return headings
            .filter((heading) => textOf(heading).includes(keyword.toLowerCase()))
            .map((heading) => heading.closest(".card") || heading.closest("section") || heading.parentElement)
            .filter(Boolean);
    }

    function insertAfterHeader(html, id) {
        if (document.getElementById(id)) {
            return;
        }

        const header = document.querySelector(".page-header") || document.querySelector("main h1")?.closest("div") || document.querySelector("main");
        if (!header) {
            return;
        }

        header.insertAdjacentHTML("afterend", html);
    }

    function setupMonitoringWorkspace() {
        if (!location.pathname.includes("/dashboard/monitoring-workspace")) {
            return;
        }

        insertAfterHeader(`
            <section id="workflowCommandBar" class="workflow-command-bar">
                <div>
                    <span class="workflow-eyebrow">Daily classroom operation</span>
                    <strong>One-click monitoring control</strong>
                    <p>Start camera, FACE attendance, and behavior monitoring together. Recording stays optional for privacy.</p>
                </div>
                <div class="workflow-command-actions">
                    <button type="button" class="btn btn-primary" id="startMonitoringAll">Start Monitoring</button>
                    <button type="button" class="btn btn-secondary" id="stopMonitoringAll">Stop Monitoring</button>
                    <span id="workflowCommandStatus" class="workflow-status-pill">Idle</span>
                </div>
            </section>
        `, "workflowCommandBar");

        const status = document.getElementById("workflowCommandStatus");

        const setStatus = (msg) => {
            if (status) {
                status.textContent = msg;
            }
        };

        const start = document.getElementById("startMonitoringAll");
        const stop = document.getElementById("stopMonitoringAll");

        if (start) {
            start.addEventListener("click", function () {
                const actions = [];

                if (safeClick("Start Camera", ["start", "camera"])) {
                    actions.push("camera");
                }

                if (safeClick("Auto Attendance ON", ["auto", "attendance", "on"])) {
                    actions.push("auto attendance");
                }

                if (
                    safeClick("Start Rule-Based Prototype", ["start", "rule"]) ||
                    safeClick("Start Auto Behavior", ["start", "auto", "behavior"]) ||
                    safeClick("Start Prototype", ["start", "prototype"])
                ) {
                    actions.push("behavior");
                }

                setStatus(actions.length ? "Monitoring started: " + actions.join(", ") : "Monitoring controls already active or unavailable");
            });
        }

        if (stop) {
            stop.addEventListener("click", function () {
                const actions = [];

                if (safeClick("Stop Camera", ["stop", "camera"])) {
                    actions.push("camera");
                }

                if (safeClick("Auto Attendance OFF", ["auto", "attendance", "off"])) {
                    actions.push("auto attendance");
                }

                if (
                    safeClick("Stop Prototype", ["stop", "prototype"]) ||
                    safeClick("Stop Auto Behavior", ["stop", "auto", "behavior"])
                ) {
                    actions.push("behavior");
                }

                setStatus(actions.length ? "Monitoring stopped: " + actions.join(", ") : "Monitoring controls already stopped or unavailable");
            });
        }
    }

    function simplifySessionAttendancePage() {
        const match = location.pathname.match(/^\/dashboard\/sessions\/(\d+)\/attendance/);
        if (!match) {
            return;
        }

        const sessionId = match[1];

        insertAfterHeader(`
            <section id="attendanceWorkflowActions" class="workflow-command-bar attendance-review-bar">
                <div>
                    <span class="workflow-eyebrow">Attendance review mode</span>
                    <strong>Review records and correct attendance</strong>
                    <p>QR scanning and FACE attendance are handled in their main pages. This page should focus on results, manual override, and review.</p>
                </div>
                <div class="workflow-command-actions">
                    <a class="btn btn-primary" href="/dashboard/qr-attendance?session_id=${sessionId}">Open QR Scanner</a>
                    <a class="btn btn-secondary" href="/dashboard/monitoring-workspace?session_id=${sessionId}">Open Monitoring</a>
                    <a class="btn btn-secondary" href="/dashboard/reports?session_id=${sessionId}">Open Reports</a>
                </div>
            </section>
        `, "attendanceWorkflowActions");

        const duplicateKeywords = [
            "qr attendance scan",
            "face recognition prototype",
            "quick demo scan"
        ];

        duplicateKeywords.forEach((keyword) => {
            findCardsByHeadingText(keyword).forEach((card) => {
                card.classList.add("is-duplicate-workflow-card");
                card.style.display = "none";
            });
        });
    }

    function compactTablesAndFeeds() {
        document.querySelectorAll(".data-table h1, .data-table h2, .data-table h3, table h1, table h2, table h3").forEach((el) => {
            el.classList.add("compact-table-heading");
        });

        document.querySelectorAll("td, th").forEach((cell) => {
            if ((cell.textContent || "").length > 28) {
                cell.classList.add("cell-wrap-safe");
            }
        });

        document.querySelectorAll("a, span, strong, b").forEach((el) => {
            const text = textOf(el);
            if (
                text.includes(".webm") ||
                text.includes(".mp4") ||
                text.includes("camera_session") ||
                text.includes("converted_camera")
            ) {
                el.classList.add("filename-compact");
            }
        });

        document.querySelectorAll("h1, h2, h3").forEach((el) => {
            const text = textOf(el);
            if (
                text === "low_confidence" ||
                text === "attention_low" ||
                text === "leaving_seat" ||
                text === "phone_usage" ||
                text === "sleeping" ||
                text === "book_usage" ||
                text === "unknown_face" ||
                text === "multiple_faces"
            ) {
                el.classList.add("event-name-compact");
            }
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        setupMonitoringWorkspace();
        simplifySessionAttendancePage();
        compactTablesAndFeeds();
    });
})();


// Phase 16.2.2 Camera Legacy UI Compact Fix
(function () {
    function normalizeEventLabel(text) {
        return (text || "")
            .replace(/\s+/g, "")
            .replace("leaving_seat", "leaving_seat")
            .replace("attention_low", "attention_low")
            .trim();
    }

    function isKnownEvent(text) {
        const value = normalizeEventLabel(text).toLowerCase();
        return [
            "leaving_seat",
            "attention_low",
            "sleeping",
            "phone_usage",
            "book_usage",
            "looking_around",
            "hand_raising",
            "no_face_detected",
            "unknown_face",
            "multiple_faces"
        ].includes(value);
    }

    function compactCameraMonitoringPage() {
        if (!window.location.pathname.includes("/dashboard/camera-monitoring")) {
            return;
        }

        document.body.classList.add("page-camera-monitoring");

        // Convert oversized raw event headings into compact badges.
        document.querySelectorAll("h1, h2, h3, h4, strong, b").forEach(function (el) {
            const raw = (el.textContent || "").trim();
            const compact = normalizeEventLabel(raw);

            if (isKnownEvent(raw)) {
                el.textContent = compact;
                el.classList.add("event-name-compact");
            }
        });

        // Compact rows near event labels.
        document.querySelectorAll(".event-name-compact").forEach(function (badge) {
            const row = badge.closest("tr") || badge.closest("li") || badge.closest("div");
            if (row) {
                row.classList.add("camera-event-row");
            }
        });

        // Make source/time looking text compact.
        document.querySelectorAll("td, span, small, p, div").forEach(function (el) {
            const text = (el.textContent || "").trim();

            if (text.includes("camera_auto_behavior_engine") || text.includes("dashboard_manual")) {
                el.classList.add("event-source");
            }

            if (/^\d{2}:\d{2}/.test(text) || /^\d{4}-\d{2}-\d{2}/.test(text)) {
                el.classList.add("event-time");
            }
        });

        // Add a clearer advanced note if not already present.
        const h1 = document.querySelector("main h1, .content h1");
        if (h1 && !document.getElementById("cameraLegacyCompactNote")) {
            const note = document.createElement("div");
            note.id = "cameraLegacyCompactNote";
            note.className = "product-note compact-note";
            note.innerHTML = "<strong>Advanced camera page:</strong> daily classroom operation should use <a href='/dashboard/monitoring-workspace'>Monitoring Workspace</a>. This page is mainly for debugging, recording history, and legacy controls.";
            h1.insertAdjacentElement("afterend", note);
        }
    }

    document.addEventListener("DOMContentLoaded", compactCameraMonitoringPage);
})();


// Phase 16.2.3 Monitoring Workspace Beauty Fix
(function () {
    function textOf(el) {
        return (el && el.textContent || "").replace(/\s+/g, " ").trim();
    }

    function normalizeEventLabel(text) {
        return (text || "")
            .replace(/\s+/g, "")
            .replace("leaving_seat", "leaving_seat")
            .replace("attention_low", "attention_low")
            .trim();
    }

    function isKnownEvent(text) {
        const value = normalizeEventLabel(text).toLowerCase();
        return [
            "leaving_seat",
            "attention_low",
            "sleeping",
            "phone_usage",
            "book_usage",
            "looking_around",
            "hand_raising",
            "no_face_detected",
            "unknown_face",
            "multiple_faces",
            "low_confidence"
        ].includes(value);
    }

    function closestCard(el) {
        return el.closest(".card") || el.closest("section") || el.closest("article") || el.parentElement;
    }

    function tagCardByHeading(keyword, className) {
        const headings = Array.from(document.querySelectorAll("h1, h2, h3, h4"));
        headings.forEach(function (heading) {
            if (textOf(heading).toLowerCase().includes(keyword.toLowerCase())) {
                const card = closestCard(heading);
                if (card) {
                    card.classList.add(className);
                }
            }
        });
    }

    function findButtonsByText(parts) {
        const buttons = Array.from(document.querySelectorAll("button, a.btn, input[type='submit']"));
        return buttons.filter(function (btn) {
            const txt = textOf(btn).toLowerCase();
            return parts.every(function (part) {
                return txt.includes(part.toLowerCase());
            });
        });
    }

    function isClosedSessionSelected() {
        const selectedText = Array.from(document.querySelectorAll("select option:checked"))
            .map(function (option) { return textOf(option); })
            .join(" ");

        const pageText = textOf(document.querySelector("main") || document.body);

        return selectedText.toLowerCase().includes("closed") ||
               pageText.toLowerCase().includes("closed/latest");
    }

    function disableMonitoringForClosedSession() {
        if (!isClosedSessionSelected()) {
            return;
        }

        const sessionCard = document.querySelector(".workspace-session-card") || document.querySelector("main");
        if (sessionCard && !document.getElementById("closedSessionMonitoringWarning")) {
            const warning = document.createElement("div");
            warning.id = "closedSessionMonitoringWarning";
            warning.className = "closed-session-warning";
            warning.innerHTML = "<div><strong>This session is closed.</strong> Monitoring should only run on an active session. Use this page for review, or create/start a new session from Sessions.</div>";
            sessionCard.insertAdjacentElement("afterbegin", warning);
        }

        findButtonsByText(["start", "monitoring"]).forEach(function (btn) {
            btn.classList.add("monitoring-disabled");
            btn.setAttribute("disabled", "disabled");
            btn.setAttribute("title", "Closed sessions cannot start monitoring.");
        });
    }

    function compactEventRows() {
        document.querySelectorAll("h1, h2, h3, h4, strong, b, span").forEach(function (el) {
            const raw = textOf(el);
            const compact = normalizeEventLabel(raw);

            if (isKnownEvent(raw)) {
                el.textContent = compact;
                el.classList.add("event-name-compact");

                const row = el.closest("tr") || el.closest("li") || el.closest("div");
                if (row) {
                    row.classList.add("workspace-feed-row");
                }
            }
        });

        document.querySelectorAll("td, span, small, p, div").forEach(function (el) {
            const text = textOf(el);

            if (text.includes("camera_auto_behavior_engine") || text.includes("dashboard_manual")) {
                el.classList.add("event-source");
            }

            if (/^\d{2}:\d{2}/.test(text) || /^\d{4}-\d{2}-\d{2}/.test(text)) {
                el.classList.add("event-time");
            }
        });
    }

    function beautifyMonitoringWorkspace() {
        if (!window.location.pathname.includes("/dashboard/monitoring-workspace")) {
            return;
        }

        document.body.classList.add("page-monitoring-workspace");

        tagCardByHeading("session control", "workspace-session-card");
        tagCardByHeading("live classroom camera", "workspace-live-camera-card");
        tagCardByHeading("auto attendance", "workspace-auto-attendance-card");
        tagCardByHeading("qr backup", "workspace-qr-card");
        tagCardByHeading("behavior monitoring", "workspace-behavior-card");
        tagCardByHeading("recording panel", "workspace-recording-card");
        tagCardByHeading("iot quick status", "workspace-iot-card");
        tagCardByHeading("detection capability", "workspace-capability-card");

        compactEventRows();
        disableMonitoringForClosedSession();
    }

    document.addEventListener("DOMContentLoaded", beautifyMonitoringWorkspace);
})();


// Phase 16.2.4 Schedule Manager UX
(function () {
    function text(el) {
        return (el && el.textContent || "").replace(/\s+/g, " ").trim();
    }

    function hideOldWeeklyScheduleCard() {
        if (!window.location.pathname.includes("/dashboard/class-setup")) return;

        const manager = document.getElementById("scheduleManager");
        if (!manager) return;

        const headings = Array.from(document.querySelectorAll("h2, h3"));
        headings.forEach(function (heading) {
            const value = text(heading).toLowerCase();

            if (value === "weekly schedule") {
                const card = heading.closest(".card") || heading.closest("section");
                if (card && card.id !== "scheduleManager") {
                    card.style.display = "none";
                }
            }
        });
    }

    document.addEventListener("DOMContentLoaded", hideOldWeeklyScheduleCard);
})();


// Phase 16.2.6 Student UI de-duplication
(function () {
    function cleanText(el) {
        return (el && el.textContent || "").replace(/\s+/g, " ").trim();
    }

    function closestCard(el) {
        return el.closest(".card") || el.closest("section") || el.closest("article") || el.parentElement;
    }

    function simplifyClassSetupStudentEnrollment() {
        if (!window.location.pathname.includes("/dashboard/class-setup")) return;

        const headings = Array.from(document.querySelectorAll("h2, h3"));
        let rosterCard = null;

        headings.forEach(function (heading) {
            const text = cleanText(heading).toLowerCase();

            if (text === "student enrollment") {
                const card = closestCard(heading);

                // Do not touch the new Add Student & Class Enrollment card
                if (card && !cleanText(card).toLowerCase().includes("add student & class enrollment")) {
                    rosterCard = card;
                    heading.textContent = "Current Class Roster";
                    card.classList.add("current-class-roster-card");

                    const paragraphs = Array.from(card.querySelectorAll("p"));
                    if (paragraphs.length) {
                        paragraphs[0].textContent = "Review students currently enrolled in the selected class. Use the lifecycle panel above to add or move students.";
                    }
                }
            }
        });

        if (!rosterCard) return;

        // Rename section headings inside old card
        Array.from(rosterCard.querySelectorAll("h3, h4, strong")).forEach(function (el) {
            const value = cleanText(el).toLowerCase();

            if (value === "enrolled students") {
                el.textContent = "Enrolled Students";
            }

            if (value === "unenrolled active students") {
                el.textContent = "Available Students";
            }
        });

        // Hide available students panel if it only says all students are enrolled
        Array.from(rosterCard.querySelectorAll("div, section, article, td")).forEach(function (el) {
            const value = cleanText(el).toLowerCase();

            if (
                value.includes("available students") &&
                value.includes("all active students are enrolled")
            ) {
                el.classList.add("hide-empty-available-students");
            }
        });

        // Make Remove action less scary/confusing
        Array.from(rosterCard.querySelectorAll("button, a")).forEach(function (el) {
            if (cleanText(el).toLowerCase() === "remove") {
                el.textContent = "Remove from class";
                el.classList.add("btn-link-soft");
                el.setAttribute("title", "This removes class enrollment only. Student record is kept.");
            }
        });
    }

    function simplifyStudentsMasterList() {
        if (!window.location.pathname.includes("/dashboard/students")) return;

        const tables = Array.from(document.querySelectorAll("table"));

        tables.forEach(function (table) {
            const headers = Array.from(table.querySelectorAll("thead th"));
            if (!headers.length) return;

            const hideIndexes = [];

            headers.forEach(function (th, index) {
                const value = cleanText(th).toUpperCase();

                if (value === "QR VALUE" || value === "FACE DATASET") {
                    hideIndexes.push(index + 1);
                }
            });

            if (!hideIndexes.length) return;

            table.classList.add("student-master-table-compact");

            hideIndexes.forEach(function (nth) {
                Array.from(table.querySelectorAll("tr")).forEach(function (row) {
                    const cell = row.children[nth - 1];
                    if (cell) {
                        cell.classList.add("hide-technical-student-column");
                    }
                });
            });

            const card = table.closest(".card") || table.parentElement;
            if (card && !card.querySelector(".student-master-note")) {
                const note = document.createElement("div");
                note.className = "student-master-note";
                note.innerHTML = "<strong>Student Master List:</strong> QR values and face dataset paths are technical details, so they are hidden here. Use Detail, QR, or Face Training when needed.";
                table.insertAdjacentElement("beforebegin", note);
            }
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        simplifyClassSetupStudentEnrollment();
        simplifyStudentsMasterList();
    });
})();


// Phase 16.2.7 Student enrollment responsibility cleanup
(function () {
    function cleanText(el) {
        return (el && el.textContent || "").replace(/\s+/g, " ").trim();
    }

    function closestCard(el) {
        return el.closest(".card") || el.closest("section") || el.closest("article") || el.parentElement;
    }

    function fixClassSetupStudentResponsibility() {
        if (!window.location.pathname.includes("/dashboard/class-setup")) return;

        // Undo the previous over-aggressive hide behavior.
        document.querySelectorAll(".hide-empty-available-students").forEach(function (el) {
            el.classList.remove("hide-empty-available-students");
        });

        // 1) Convert "Add Student & Class Enrollment" into "Class Enrollment Actions"
        const headings = Array.from(document.querySelectorAll("h2, h3"));
        let lifecycleCard = null;

        headings.forEach(function (heading) {
            const value = cleanText(heading).toLowerCase();

            if (value.includes("add student & class enrollment")) {
                lifecycleCard = closestCard(heading);
                heading.textContent = "Class Enrollment Actions";

                const intro = lifecycleCard ? lifecycleCard.querySelector("p") : null;
                if (intro) {
                    intro.textContent = "Create student identity from the Students page. Use this section only to enroll, move, or manage students inside a class.";
                }
            }
        });

        if (lifecycleCard) {
            lifecycleCard.classList.add("class-enrollment-actions-card");

            if (!lifecycleCard.querySelector(".class-enrollment-routing-note")) {
                const note = document.createElement("div");
                note.className = "class-enrollment-routing-note";
                note.innerHTML = '<strong>Workflow:</strong> New student → <a href="/dashboard/students">Students page</a>. Class assignment or move → Class Setup.';
                const firstGrid = lifecycleCard.querySelector(".student-lifecycle-grid");
                if (firstGrid) {
                    firstGrid.insertAdjacentElement("beforebegin", note);
                }
            }

            const grid = lifecycleCard.querySelector(".student-lifecycle-grid");
            if (grid) {
                grid.classList.add("enrollment-actions-grid-clean");
            }

            const panels = Array.from(lifecycleCard.querySelectorAll(".student-lifecycle-panel"));

            panels.forEach(function (panel) {
                const text = cleanText(panel).toLowerCase();
                const panelHeading = panel.querySelector("h3");

                // Hide duplicate student creation form from Class Setup.
                if (text.includes("add student to class") && text.includes("student name")) {
                    panel.classList.add("hide-class-setup-create-student");
                }

                // Keep and clarify move/enroll panel.
                if (text.includes("move student to another class")) {
                    panel.classList.add("enroll-move-panel-clean");

                    if (panelHeading) {
                        panelHeading.textContent = "Enroll / Move Student to Class";
                    }

                    const safeNote = panel.querySelector(".safe-note");
                    if (safeNote) {
                        safeNote.textContent = "Use this when a student joins this class or moves from another class. Old enrollment is deactivated, but student history remains.";
                    }

                    const button = panel.querySelector("button");
                    if (button && cleanText(button).toLowerCase().includes("move")) {
                        button.textContent = "Save Class Enrollment";
                    }
                }
            });
        }

        // 2) Make roster section a real roster again.
        const allHeadings = Array.from(document.querySelectorAll("h2, h3"));
        let rosterCard = null;

        allHeadings.forEach(function (heading) {
            const value = cleanText(heading).toLowerCase();

            if (value === "current class roster" || value === "student enrollment") {
                const card = closestCard(heading);

                if (card && !cleanText(card).toLowerCase().includes("class enrollment actions")) {
                    rosterCard = card;
                    card.classList.add("class-roster-manager-card");
                    heading.textContent = "Current Class Roster";

                    const p = card.querySelector("p");
                    if (p) {
                        p.textContent = "View students in the selected class and available students who can be enrolled.";
                    }
                }
            }
        });

        if (rosterCard) {
            // Make any hidden available/enrolled areas visible again.
            rosterCard.querySelectorAll("*").forEach(function (el) {
                if (el.style && el.style.display === "none") {
                    const text = cleanText(el).toLowerCase();
                    if (text.includes("enrolled students") || text.includes("unenrolled") || text.includes("available students")) {
                        el.style.display = "";
                    }
                }
            });

            Array.from(rosterCard.querySelectorAll("h3, h4, strong")).forEach(function (el) {
                const value = cleanText(el).toLowerCase();

                if (value === "enrolled students") {
                    el.textContent = "Students in This Class";
                }

                if (value === "unenrolled active students" || value === "available students") {
                    el.textContent = "Available / Unassigned Students";
                }
            });

            Array.from(rosterCard.querySelectorAll("button, a")).forEach(function (el) {
                const value = cleanText(el).toLowerCase();

                if (value === "remove") {
                    el.textContent = "Remove from class";
                    el.classList.add("btn-link-soft");
                    el.setAttribute("title", "This removes class enrollment only. Student identity and history are kept.");
                }

                if (value === "add" || value === "enroll") {
                    el.textContent = "Enroll to class";
                }
            });

            if (!rosterCard.querySelector(".roster-manager-note")) {
                const note = document.createElement("div");
                note.className = "roster-manager-note";
                note.innerHTML = "<strong>Roster rule:</strong> Removing from class does not delete the student. It only changes enrollment.";
                const select = rosterCard.querySelector("select");
                if (select) {
                    select.closest("form, div").insertAdjacentElement("afterend", note);
                }
            }
        }

        // 3) Students page note
        if (window.location.pathname.includes("/dashboard/students")) {
            const addHeading = Array.from(document.querySelectorAll("h2, h3"))
                .find(function (h) { return cleanText(h).toLowerCase() === "add student"; });

            if (addHeading) {
                const card = closestCard(addHeading);
                if (card && !card.querySelector(".student-identity-note")) {
                    const note = document.createElement("div");
                    note.className = "student-identity-note";
                    note.innerHTML = "<strong>Student identity only:</strong> Create the student here. Assign or move class in Class Setup.";
                    addHeading.insertAdjacentElement("afterend", note);
                }
            }
        }
    }

    document.addEventListener("DOMContentLoaded", fixClassSetupStudentResponsibility);
})();


// Phase 17C Unified Monitoring Workspace Object Detection Panel
(function () {
    const STREAM_BASE = "/api/object-detection/stream?camera_index=0";

    function isWorkspace() {
        return window.location.pathname.includes("/dashboard/monitoring-workspace");
    }

    function text(el) {
        return (el && el.textContent || "").replace(/\s+/g, " ").trim();
    }

    function findButtonByText(words) {
        const buttons = Array.from(document.querySelectorAll("button, a"));
        return buttons.find(function (btn) {
            const value = text(btn).toLowerCase();
            return words.every(function (word) {
                return value.includes(word);
            });
        });
    }

    function ensurePanel() {
        if (!isWorkspace()) return null;

        let panel = document.querySelector(".workspace-object-detection-panel");
        if (panel) return panel;

        panel = document.createElement("section");
        panel.className = "card workspace-object-detection-panel";
        panel.innerHTML = `
            <div class="workspace-od-head">
                <div>
                    <p class="eyebrow">Object Detection</p>
                    <h2>Phone / Book Detection</h2>
                    <p class="muted workspace-od-message">Checking model status...</p>
                </div>
                <span class="workspace-od-pill">Checking</span>
            </div>

            <div class="workspace-od-controls">
                <button type="button" class="btn btn-primary workspace-od-start">Start Object Detection</button>
                <button type="button" class="btn btn-secondary workspace-od-stop">Stop</button>
                <a class="btn btn-secondary" href="/dashboard/object-detection">Debug Page</a>
            </div>

            <div class="workspace-od-stream-wrap is-idle">
                <div class="workspace-od-placeholder">
                    Click <strong>Start Monitoring</strong> or <strong>Start Object Detection</strong> to start phone/book overlay.
                </div>
                <img class="workspace-od-stream" alt="Phone and book detection stream">
            </div>

            <div class="workspace-od-hint">
                <strong>Unified workflow:</strong>
                Start Monitoring should run camera, face attendance, behavior detection, and phone/book detection together.
            </div>
        `;

        const targetHeading = Array.from(document.querySelectorAll("h2, h3"))
            .find(function (h) {
                const value = text(h).toLowerCase();
                return value.includes("live") || value.includes("camera") || value.includes("monitoring");
            });

        if (targetHeading) {
            const card = targetHeading.closest(".card") || targetHeading.closest("section") || targetHeading.parentElement;
            card.insertAdjacentElement("afterend", panel);
        } else {
            const main = document.querySelector("main") || document.querySelector(".content") || document.body;
            main.appendChild(panel);
        }

        return panel;
    }

    function setStatus(panel, status) {
        const pill = panel.querySelector(".workspace-od-pill");
        const message = panel.querySelector(".workspace-od-message");

        if (!pill || !message) return;

        if (status.enabled) {
            pill.textContent = "Ready";
            pill.className = "workspace-od-pill ready";
            message.textContent = "YOLO model is ready. Phone, book, and person boxes can be shown.";
        } else {
            pill.textContent = "Model Missing";
            pill.className = "workspace-od-pill warning";
            message.textContent = status.message || "Object detection model is not installed.";
        }
    }

    function refreshStatus(panel) {
        fetch("/api/object-detection/status")
            .then(function (res) { return res.json(); })
            .then(function (data) { setStatus(panel, data); })
            .catch(function () {
                const pill = panel.querySelector(".workspace-od-pill");
                const message = panel.querySelector(".workspace-od-message");
                if (pill) {
                    pill.textContent = "Offline";
                    pill.className = "workspace-od-pill warning";
                }
                if (message) {
                    message.textContent = "Could not read object detection status.";
                }
            });
    }

    function startObjectDetection(panel) {
        const img = panel.querySelector(".workspace-od-stream");
        const wrap = panel.querySelector(".workspace-od-stream-wrap");

        if (!img || !wrap) return;

        wrap.classList.remove("is-idle");
        wrap.classList.add("is-running");

        img.src = STREAM_BASE + "&t=" + Date.now();
    }

    function stopObjectDetection(panel) {
        const img = panel.querySelector(".workspace-od-stream");
        const wrap = panel.querySelector(".workspace-od-stream-wrap");

        if (!img || !wrap) return;

        img.removeAttribute("src");
        wrap.classList.add("is-idle");
        wrap.classList.remove("is-running");
    }

    function bindPanel(panel) {
        const startBtn = panel.querySelector(".workspace-od-start");
        const stopBtn = panel.querySelector(".workspace-od-stop");

        if (startBtn && !startBtn.dataset.bound) {
            startBtn.dataset.bound = "1";
            startBtn.addEventListener("click", function () {
                startObjectDetection(panel);
            });
        }

        if (stopBtn && !stopBtn.dataset.bound) {
            stopBtn.dataset.bound = "1";
            stopBtn.addEventListener("click", function () {
                stopObjectDetection(panel);
            });
        }

        const mainStart = findButtonByText(["start", "monitor"]);
        if (mainStart && !mainStart.dataset.objectDetectionBound) {
            mainStart.dataset.objectDetectionBound = "1";
            mainStart.addEventListener("click", function () {
                setTimeout(function () {
                    startObjectDetection(panel);
                }, 700);
            });
        }

        const mainStop = findButtonByText(["stop"]);
        if (mainStop && !mainStop.dataset.objectDetectionStopBound) {
            mainStop.dataset.objectDetectionStopBound = "1";
            mainStop.addEventListener("click", function () {
                stopObjectDetection(panel);
            });
        }
    }

    function init() {
        if (!isWorkspace()) return;

        const panel = ensurePanel();
        if (!panel) return;

        refreshStatus(panel);
        bindPanel(panel);

        setInterval(function () {
            if (document.body.contains(panel)) {
                refreshStatus(panel);
            }
        }, 10000);
    }

    document.addEventListener("DOMContentLoaded", init);
})();
