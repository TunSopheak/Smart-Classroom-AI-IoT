from pathlib import Path

css_path = Path("app/static/css/styles.css")
css = css_path.read_text(encoding="utf-8")

phase4_css = r'''

/* Phase 4 Face recognition foundation */
.face-panel {
    border-left: 5px solid #8b5cf6;
}

.quick-face-list {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 14px;
}

.face-chip {
    background: #f5f3ff !important;
    color: #6d28d9 !important;
    border: 1px solid #ddd6fe !important;
    font-size: 12px !important;
    padding: 8px 10px !important;
}

.note-box {
    margin-top: 18px;
    padding: 14px;
    border-radius: 14px;
    border: 1px solid #ddd6fe;
    background: #f5f3ff;
}

.phase-action-form {
    margin-top: 18px;
}
'''

if "/* Phase 4 Face recognition foundation */" not in css:
    css_path.write_text(css + phase4_css, encoding="utf-8")

print("Step 7 done: CSS added.")
