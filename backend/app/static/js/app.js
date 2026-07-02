(() => {
    const sidebar = document.querySelector("#dashboard-sidebar");
    const toggle = document.querySelector("[data-sidebar-toggle]");
    const closeTargets = document.querySelectorAll("[data-sidebar-close]");

    if (!sidebar || !toggle) return;

    const setSidebarOpen = (isOpen) => {
        document.documentElement.classList.toggle("sidebar-open", isOpen);
        document.body.classList.toggle("sidebar-open", isOpen);
        toggle.setAttribute("aria-expanded", String(isOpen));
        toggle.setAttribute("aria-label", isOpen ? "Close navigation" : "Open navigation");
        sidebar.setAttribute("aria-hidden", String(!isOpen && window.innerWidth <= 860));
    };

    const toggleSidebar = (event) => {
        event.preventDefault();
        event.stopPropagation();
        setSidebarOpen(!document.body.classList.contains("sidebar-open"));
    };

    toggle.addEventListener("click", toggleSidebar);
    toggle.addEventListener("touchend", toggleSidebar, { passive: false });

    closeTargets.forEach((target) => {
        target.addEventListener("click", () => setSidebarOpen(false));
        target.addEventListener("touchend", (event) => {
            event.preventDefault();
            setSidebarOpen(false);
        }, { passive: false });
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

    setSidebarOpen(false);
})();
