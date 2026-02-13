// Name search + pin for the general mobile view
// Pin stores attendee name in localStorage, auto-applies on page load and round changes
(function () {
    const STORAGE_KEY = "matchmaking_pinned_name";

    function getPinnedName() {
        return localStorage.getItem(STORAGE_KEY) || "";
    }

    function setPinnedName(name) {
        if (name) {
            localStorage.setItem(STORAGE_KEY, name);
        } else {
            localStorage.removeItem(STORAGE_KEY);
        }
    }

    function filterPairings(query) {
        const rows = document.querySelectorAll("[data-pairing-row]");
        const normalizedQuery = query.toLowerCase().trim();

        rows.forEach((row) => {
            if (!normalizedQuery) {
                row.style.display = "";
                return;
            }
            const names = row.getAttribute("data-pairing-names") || "";
            row.style.display = names.toLowerCase().includes(normalizedQuery)
                ? ""
                : "none";
        });
    }

    function init() {
        const searchInput = document.getElementById("search-input");
        const pinButton = document.getElementById("pin-button");
        const clearButton = document.getElementById("clear-pin");

        if (!searchInput) return;

        const pinned = getPinnedName();
        if (pinned) {
            searchInput.value = pinned;
            filterPairings(pinned);
            if (pinButton) pinButton.classList.add("bg-blue-500", "text-white");
        }

        searchInput.addEventListener("input", () => {
            filterPairings(searchInput.value);
        });

        if (pinButton) {
            pinButton.addEventListener("click", () => {
                const name = searchInput.value.trim();
                if (name) {
                    setPinnedName(name);
                    pinButton.classList.add("bg-blue-500", "text-white");
                }
            });
        }

        if (clearButton) {
            clearButton.addEventListener("click", () => {
                setPinnedName("");
                searchInput.value = "";
                filterPairings("");
                if (pinButton) pinButton.classList.remove("bg-blue-500", "text-white");
            });
        }
    }

    // Re-apply filter after HTMX swaps new content
    document.addEventListener("htmx:afterSwap", () => {
        const pinned = getPinnedName();
        if (pinned) filterPairings(pinned);
    });

    // Init on DOM ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
