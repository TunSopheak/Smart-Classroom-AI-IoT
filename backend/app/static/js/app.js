console.log("Smart Classroom AI IoT dashboard loaded.");

(() => {
    const sidebar = document.querySelector("#dashboard-sidebar");
    const toggle = document.querySelector("[data-sidebar-toggle]");
    const closeTargets = document.querySelectorAll("[data-sidebar-close]");

    if (!sidebar || !toggle) return;

    const setSidebarOpen = (isOpen) => {
        document.body.classList.toggle("sidebar-open", isOpen);
        toggle.setAttribute("aria-expanded", String(isOpen));
    };

    toggle.addEventListener("click", () => {
        setSidebarOpen(!document.body.classList.contains("sidebar-open"));
    });

    closeTargets.forEach((target) => {
        target.addEventListener("click", () => setSidebarOpen(false));
    });

    sidebar.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", () => setSidebarOpen(false));
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") setSidebarOpen(false);
    });

    window.addEventListener("resize", () => {
        if (window.innerWidth > 860) setSidebarOpen(false);
    });
})();
