// Countdown timer — receives timerEnd ISO timestamp from SSE, renders countdown
// Server-authoritative: server sends target timestamp, client counts down
(function () {
    let timerEnd = null;
    let paused = false;
    let pausedRemaining = null;
    let intervalId = null;
    const timerElement = () => document.getElementById("timer-display");

    function formatTime(totalSeconds) {
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${minutes}:${String(seconds).padStart(2, "0")}`;
    }

    function updateDisplay() {
        const element = timerElement();
        if (!element) return;

        if (paused && pausedRemaining !== null) {
            element.textContent = formatTime(pausedRemaining);
            element.classList.add("text-yellow-500");
            element.classList.remove("text-red-500", "animate-pulse");
            return;
        }

        if (!timerEnd) {
            element.textContent = "--:--";
            element.classList.remove("text-red-500", "animate-pulse", "text-yellow-500");
            return;
        }

        const now = Date.now();
        const remaining = Math.max(0, Math.ceil((timerEnd - now) / 1000));

        element.textContent = formatTime(remaining);
        element.classList.remove("text-yellow-500");

        if (remaining <= 0) {
            element.classList.add("text-red-500", "animate-pulse");
        } else if (remaining <= 60) {
            element.classList.add("text-red-500");
            element.classList.remove("animate-pulse");
        } else {
            element.classList.remove("text-red-500", "animate-pulse");
        }
    }

    function startCountdown() {
        if (intervalId) clearInterval(intervalId);
        intervalId = setInterval(updateDisplay, 250);
        updateDisplay();
    }

    // Public API — called from SSE event handlers
    window.Timer = {
        setEnd(isoTimestamp) {
            timerEnd = new Date(isoTimestamp).getTime();
            paused = false;
            pausedRemaining = null;
            startCountdown();
        },
        pause(remainingSeconds) {
            paused = true;
            pausedRemaining = remainingSeconds;
            updateDisplay();
        },
        resume(isoTimestamp) {
            timerEnd = new Date(isoTimestamp).getTime();
            paused = false;
            pausedRemaining = null;
            startCountdown();
        },
        clear() {
            timerEnd = null;
            paused = false;
            pausedRemaining = null;
            if (intervalId) clearInterval(intervalId);
            updateDisplay();
        },
    };
})();
