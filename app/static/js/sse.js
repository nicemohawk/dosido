// SSE connection using native EventSource.
// Dispatches "sse:<event>" CustomEvents on document.body so view scripts
// can listen with: document.body.addEventListener("sse:round_update", ...)
//
// Polling fallback: if <body data-sse-poll-ms="5000"> is set, an "sse:poll"
// event fires on that interval while the connection is down, so views can
// refresh themselves. Polling stops as soon as SSE reconnects.
(function () {
    var SSE_EVENTS = ["round_update", "timer_update", "checkin_update", "signal_update", "heartbeat"];
    var source = null;
    var reconnectDelay = 1000;
    var wasConnected = false;
    var pollIntervalMs = parseInt(document.body.dataset.ssePollMs || "0", 10);
    var pollTimer = null;

    function startPolling() {
        if (!pollIntervalMs || pollTimer) return;
        console.warn("[SSE] connection down — polling every " + pollIntervalMs / 1000 + "s as fallback");
        pollTimer = setInterval(function () {
            document.body.dispatchEvent(new CustomEvent("sse:poll"));
        }, pollIntervalMs);
    }

    function stopPolling() {
        if (!pollTimer) return;
        clearInterval(pollTimer);
        pollTimer = null;
        console.info("[SSE] polling fallback stopped");
    }

    function connect() {
        source = new EventSource("/api/state/stream");

        source.onopen = function () {
            reconnectDelay = 1000;
            stopPolling();
            document.body.dispatchEvent(new CustomEvent("sse:open"));
            if (wasConnected) {
                // Reconnected after a drop — may have missed events
                console.info("[SSE] reconnected");
                document.body.dispatchEvent(new CustomEvent("sse:reconnected"));
            }
            wasConnected = true;
        };

        source.onerror = function () {
            console.warn("[SSE] connection error — reconnecting in " + reconnectDelay / 1000 + "s");
            document.body.dispatchEvent(new CustomEvent("sse:error"));
            source.close();
            startPolling();
            setTimeout(connect, reconnectDelay);
            reconnectDelay = Math.min(reconnectDelay * 2, 30000);
        };

        SSE_EVENTS.forEach(function (name) {
            source.addEventListener(name, function (e) {
                document.body.dispatchEvent(
                    new CustomEvent("sse:" + name, {
                        bubbles: true,
                        detail: { data: e.data },
                    })
                );
            });
        });
    }

    connect();
})();
