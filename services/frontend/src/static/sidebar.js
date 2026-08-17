const sidebar = document.getElementById("app-sidebar");
const toggle = document.getElementById("sidebar-toggle");

if (sidebar && toggle) {

    const savedState =
        localStorage.getItem("stocksguru-sidebar-collapsed");

    if (savedState === "true") {
        sidebar.classList.add("collapsed");
        toggle.setAttribute("aria-expanded", "false");
    }

    toggle.addEventListener("click", () => {

        sidebar.classList.toggle("collapsed");

        const collapsed =
            sidebar.classList.contains("collapsed");

        toggle.setAttribute(
            "aria-expanded",
            String(!collapsed)
        );

        localStorage.setItem(
            "stocksguru-sidebar-collapsed",
            String(collapsed)
        );

    });

}