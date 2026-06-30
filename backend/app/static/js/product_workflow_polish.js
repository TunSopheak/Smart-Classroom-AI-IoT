
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
