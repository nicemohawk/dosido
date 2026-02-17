// SSE connection using native EventSource.
// Dispatches "sse:<event>" CustomEvents on document.body so view scripts
// can listen with: document.body.addEventListener("sse:round_update", ...)
(function () {
    var SSE_EVENTS = ["round_update", "timer_update", "checkin_update", "signal_update", "heartbeat"];
    var source = null;
    var reconnectDelay = 1000;
    var wasConnected = false;

    function connect() {
        source = new EventSource("/api/state/stream");

        source.onopen = function () {
            reconnectDelay = 1000;
            document.body.dispatchEvent(new CustomEvent("sse:open"));
            if (wasConnected) {
                // Reconnected after a drop — may have missed events
                document.body.dispatchEvent(new CustomEvent("sse:reconnected"));
            }
            wasConnected = true;
        };

        source.onerror = function () {
            document.body.dispatchEvent(new CustomEvent("sse:error"));
            source.close();
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
