/**
 * Standalone beat-time widget updater for the header.
 * Uses Swatch Internet Time (BMT = UTC+1).
 */
(function () {
    function setupBeatTimeWidget() {
        const beatValueEl = document.getElementById('beat-time-value');
        const beatStatusEl = document.getElementById('beat-time-status');
        if (!beatValueEl || !beatStatusEl) return;

        function updateBeatTime() {
            const now = new Date();
            const utcHours = now.getUTCHours();
            const utcMinutes = now.getUTCMinutes();
            const utcSeconds = now.getUTCSeconds();
            const utcMilliseconds = now.getUTCMilliseconds();

            const bmtSeconds = ((utcHours + 1) % 24) * 3600 + utcMinutes * 60 + utcSeconds + (utcMilliseconds / 1000);
            const beatTime = bmtSeconds / 86.4;
            const beatInt = Math.floor(beatTime);
            const beatDisplay = `@${beatTime.toFixed(2).padStart(6, '0')}`;
            const firstDigit = String(beatInt).padStart(3, '0').charAt(0);
            const firstDigitNum = parseInt(firstDigit, 10);
            const isEven = Number.isFinite(firstDigitNum) && (firstDigitNum % 2 === 0);

            beatValueEl.textContent = beatDisplay;
            beatStatusEl.textContent = isEven ? 'Divine Punishment ACTIVE' : 'Divine Punishment INACTIVE';
            beatStatusEl.classList.toggle('beat-time-status-active', isEven);
            beatStatusEl.classList.toggle('beat-time-status-inactive', !isEven);
        }

        updateBeatTime();
        setInterval(updateBeatTime, 100);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupBeatTimeWidget);
    } else {
        setupBeatTimeWidget();
    }
})();
