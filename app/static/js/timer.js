// Countdown timer — receives timerEnd ISO timestamp from SSE, renders countdown
// Server-authoritative: server sends target timestamp, client counts down
(function () {
    const TIMER_CLASSES = ["timer-warning", "timer-expired", "timer-paused"];

    let timerEnd = null;
    let paused = false;
    let pausedRemaining = null;
    let intervalId = null;
    let expireCallback = null;
    let expireFired = false;
    const timerElement = () => document.getElementById("timer-display");

    function formatTime(totalSeconds) {
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${minutes}:${String(seconds).padStart(2, "0")}`;
    }

    function clearTimerClasses(element) {
        element.classList.remove(...TIMER_CLASSES);
    }

    function updateDisplay() {
        const element = timerElement();
        if (!element) return;

        if (paused && pausedRemaining !== null) {
            element.textContent = formatTime(pausedRemaining);
            clearTimerClasses(element);
            element.classList.add("timer-paused");
            return;
        }

        if (!timerEnd) {
            element.textContent = "--:--";
            clearTimerClasses(element);
            return;
        }

        const now = Date.now();
        const remaining = Math.max(0, Math.ceil((timerEnd - now) / 1000));

        element.textContent = formatTime(remaining);
        clearTimerClasses(element);

        if (remaining <= 0) {
            element.classList.add("timer-expired");
            if (!expireFired && expireCallback) {
                expireFired = true;
                expireCallback();
            }
        } else if (remaining <= 60) {
            element.classList.add("timer-warning");
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
            expireFired = false;
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
            expireFired = false;
            if (intervalId) clearInterval(intervalId);
            updateDisplay();
        },
        onExpire(callback) {
            expireCallback = callback;
        },
    };
})();
