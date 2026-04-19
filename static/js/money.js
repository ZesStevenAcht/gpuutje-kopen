(function () {
    const moneyImages = [
        "/static/falling_money/Paper_money_small_2x2_r0_c0.png",
        "/static/falling_money/Paper_money_small_2x2_r0_c1.png",
        "/static/falling_money/Paper_money_small_2x2_r1_c0.png",
        "/static/falling_money/Paper_money_small_2x2_r1_c1.png",
        "/static/falling_money/coins_small_4x2_r0_c0.png",
        "/static/falling_money/coins_small_4x2_r0_c1.png",
        "/static/falling_money/coins_small_4x2_r0_c2.png",
        "/static/falling_money/coins_small_4x2_r0_c3.png",
        "/static/falling_money/coins_small_4x2_r1_c0.png",
        "/static/falling_money/coins_small_4x2_r1_c1.png",
        "/static/falling_money/coins_small_4x2_r1_c2.png",
        "/static/falling_money/coins_small_4x2_r1_c3.png",
    ];

    const canvas = document.getElementById("money-canvas");
    const MAX_ITEMS = 30;
    let active = 0;

    function spawnMoney() {
        if (active >= MAX_ITEMS) return;
        active++;

        const img = document.createElement("img");
        img.src = moneyImages[Math.floor(Math.random() * moneyImages.length)];
        img.style.left = Math.random() * 100 + "vw";
        img.style.top = "-60px";
        img.style.opacity = 0.35 + Math.random() * 0.3;

        const size = 24 + Math.random() * 32;
        img.style.width = size + "px";
        img.style.height = "auto";

        const rotation = Math.random() * 360;
        const drift = (Math.random() - 0.5) * 80;
        const duration = 6000 + Math.random() * 8000;
        const wobble = (Math.random() - 0.5) * 40;

        canvas.appendChild(img);

        const start = performance.now();
        function animate(now) {
            const t = (now - start) / duration;
            if (t >= 1) {
                img.remove();
                active--;
                return;
            }
            const y = t * (window.innerHeight + 80);
            const x = drift * t + wobble * Math.sin(t * Math.PI * 3);
            const rot = rotation + t * 180;
            img.style.transform = `translate(${x}px, ${y}px) rotate(${rot}deg)`;
            requestAnimationFrame(animate);
        }
        requestAnimationFrame(animate);
    }

    setInterval(spawnMoney, 300);
})();
