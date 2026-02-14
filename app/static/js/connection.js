// Connection status indicator — monitors SSE connection health
(function () {
    const el = document.getElementById("connection-status");
    if (!el) return;

    let lastEventTime = 0;
    let checkInterval = null;
    let isConnected = false;
    let hideTimeout = null;

    function show(message, classes) {
        el.textContent = message;
        el.className =
            "fixed bottom-3 right-3 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-300 z-50 " +
            classes;

        // Clear any pending hide
        if (hideTimeout) clearTimeout(hideTimeout);
    }

    function hideAfterDelay(ms) {
        if (hideTimeout) clearTimeout(hideTimeout);
        hideTimeout = setTimeout(() => {
            el.classList.add("opacity-0", "pointer-events-none");
        }, ms);
    }

    function showConnected() {
        if (!isConnected) {
            isConnected = true;
            show("Connected", "bg-green-100 text-green-700 opacity-100");
            hideAfterDelay(3000);
        }
    }

    function showDisconnected() {
        isConnected = false;
        show("Reconnecting...", "bg-red-100 text-red-700 opacity-100");
    }

    function showStale(seconds) {
        show("Last update: " + seconds + "s ago", "bg-yellow-100 text-yellow-700 opacity-100");
    }

    // SSE connection events (from sse.js)
    document.body.addEventListener("sse:open", function () {
        lastEventTime = Date.now();
        showConnected();
    });

    document.body.addEventListener("sse:error", function () {
        showDisconnected();
    });

    // Track any SSE message as a sign of connection health
    ["sse:round_update", "sse:timer_update", "sse:checkin_update", "sse:signal_update"].forEach(
        function (eventName) {
            document.body.addEventListener(eventName, function () {
                lastEventTime = Date.now();
                if (!isConnected) showConnected();
            });
        }
    );

    // Periodic staleness check — if no event received in 30s, show warning
    checkInterval = setInterval(function () {
        if (lastEventTime === 0) return;
        var elapsed = Math.floor((Date.now() - lastEventTime) / 1000);
        if (elapsed > 30 && isConnected) {
            showStale(elapsed);
        }
    }, 5000);
})();
