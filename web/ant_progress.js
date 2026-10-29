/**
 * Organix Custom Ant Walking Progress Bar
 * ========================================
 * Cycles 8 transparent PNG frames (1-ant.png -> 8-ant.png) at ~10 FPS (100ms)
 * Continuous walking animation across a glowing progress track.
 * Supports single or multi-ant marching.
 * High-contrast white track background and white rim glow ensures 100% visibility.
 * Positioned right at the leading end of the orange progress bar.
 */
class OrganixAntProgressBar {
    constructor(options = {}) {
        this.container = typeof options.container === 'string' 
            ? document.getElementById(options.container) 
            : (options.container || document.body);
            
        this.numAnts = options.numAnts || 1;
        this.antSize = options.antSize || 52; // px width
        this.fps = options.fps || 10; // 10 fps (~100ms)
        this.frameInterval = 1000 / this.fps;
        
        // 8 walking animation frames
        this.frames = options.frames || [
            '/ant/1-ant.png',
            '/ant/2-ant.png',
            '/ant/3-ant.png',
            '/ant/4-ant.png',
            '/ant/5-ant.png',
            '/ant/6-ant.png',
            '/ant/7-ant.png',
            '/ant/8-ant.png'
        ];
        
        this.currentPercent = 0;
        this.targetPercent = 0;
        this.animationTimer = null;
        
        // Preload images for flicker-free playback
        this.preloadedImages = [];
        this.preloadFrames();
        
        // Ants state array (ready to support multiple ants)
        this.ants = [];
        for (let i = 0; i < this.numAnts; i++) {
            this.ants.push({
                id: i,
                frameIndex: (i * 2) % this.frames.length,
                offsetPercent: (i * -6),
                element: null
            });
        }
        
        this.render();
        this.startLoop();
    }
    
    preloadFrames() {
        this.frames.forEach((src) => {
            const img = new Image();
            img.src = src;
            this.preloadedImages.push(img);
        });
    }
    
    render() {
        this.wrapper = document.createElement('div');
        this.wrapper.className = 'organix-ant-progress-wrapper w-full select-none';
        this.wrapper.innerHTML = `
            <div class="flex items-center justify-between text-xs mb-1 font-sans">
                <span class="font-bold text-slate-900 dark:text-white organix-progress-title flex items-center space-x-2">
                    <span class="w-2.5 h-2.5 rounded-full bg-amber-500 animate-ping"></span>
                    <span class="progress-title-text text-sm font-extrabold tracking-tight">Organizing Files</span>
                </span>
                <span class="font-mono font-extrabold text-sm text-amber-500 dark:text-amber-400 organix-progress-percent">0%</span>
            </div>
            
            <!-- Progress Track Container with relative positioning for walking ant -->
            <div class="relative w-full pt-10 pb-1">
                <!-- Ants Stage Overlay -->
                <div class="organix-ants-stage absolute inset-x-0 top-0 h-14 pointer-events-none overflow-visible">
                    <!-- Ant element(s) inserted here -->
                </div>
                
                <!-- Track Bar Background (Crisp White / Light Track for optimal contrast) -->
                <div class="organix-progress-track relative w-full h-3.5 bg-white/90 dark:bg-white/85 rounded-full overflow-hidden border border-slate-300 dark:border-white/30 shadow-inner">
                    <!-- Glow Fill Behind the Ant -->
                    <div class="organix-progress-fill h-full bg-gradient-to-r from-amber-500 via-orange-500 to-amber-400 rounded-full transition-all duration-150 ease-out shadow-sm shadow-amber-500/30" style="width: 0%"></div>
                </div>
            </div>
            
            <div class="flex items-center justify-between text-[11px] text-slate-400 mt-2 font-mono">
                <span class="organix-progress-status truncate max-w-xs sm:max-w-md font-medium text-slate-600 dark:text-slate-300">Organix Engine Ready...</span>
                <span class="organix-progress-eta text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold flex items-center space-x-1">
                    <i class="fa-solid fa-shield-halved text-[9px]"></i>
                    <span>Zero Loss Active</span>
                </span>
            </div>
        `;
        
        this.container.appendChild(this.wrapper);
        
        this.titleText = this.wrapper.querySelector('.progress-title-text');
        this.percentText = this.wrapper.querySelector('.organix-progress-percent');
        this.statusText = this.wrapper.querySelector('.organix-progress-status');
        this.fillBar = this.wrapper.querySelector('.organix-progress-fill');
        this.stage = this.wrapper.querySelector('.organix-ants-stage');
        this.track = this.wrapper.querySelector('.organix-progress-track');
        
        // Create Ant DOM Elements with White Rim Glow & positioned at end of orange progress
        this.ants.forEach(ant => {
            const antImg = document.createElement('img');
            antImg.src = this.frames[ant.frameIndex];
            antImg.alt = "Walking Ant";
            antImg.className = "absolute pointer-events-none select-none transition-transform duration-100 ease-linear";
            antImg.style.width = `${this.antSize}px`;
            antImg.style.height = `${this.antSize}px`;
            antImg.style.top = `-12px`; // sits precisely with feet on track
            antImg.style.left = `0%`;
            // Position ant at the leading end of the orange progress (leading the progress line)
            antImg.style.transform = `translateX(-78%)`;
            antImg.style.objectFit = 'contain';
            antImg.style.zIndex = '10';
            // Crisp White Backlight Rim Glow for 100% visibility on all backgrounds:
            antImg.style.filter = "drop-shadow(0 0 3px rgba(255, 255, 255, 0.95)) drop-shadow(0 0 8px rgba(245, 158, 11, 0.6))";
            this.stage.appendChild(antImg);
            ant.element = antImg;
        });
    }
    
    startLoop() {
        if (this.animationTimer) clearInterval(this.animationTimer);
        this.animationTimer = setInterval(() => {
            this.tick();
        }, this.frameInterval);
    }
    
    tick() {
        // Continuous cycle through frames 0 -> 7 -> 0 (always walking even when progress is stationary)
        this.ants.forEach(ant => {
            ant.frameIndex = (ant.frameIndex + 1) % this.frames.length;
            if (ant.element) {
                ant.element.src = this.frames[ant.frameIndex];
            }
        });
        
        // Smoothly interpolate currentPercent towards targetPercent
        const diff = this.targetPercent - this.currentPercent;
        if (Math.abs(diff) > 0.1) {
            this.currentPercent += diff * 0.25;
        } else {
            this.currentPercent = this.targetPercent;
        }
        
        this.updatePosition();
    }
    
    updatePosition() {
        const p = Math.max(0, Math.min(100, this.currentPercent));
        
        // Update bar fill behind the ant
        if (this.fillBar) {
            this.fillBar.style.width = `${p}%`;
        }
        if (this.percentText) {
            this.percentText.textContent = `${Math.round(p)}%`;
        }
        
        // Update Ant position:
        // Positioned at the end of the orange progress
        this.ants.forEach(ant => {
            if (ant.element) {
                const antP = Math.max(0, Math.min(100, p + ant.offsetPercent));
                ant.element.style.left = `${antP}%`;
            }
        });
    }
    
    setProgress(percent, statusMessage = null) {
        this.targetPercent = Math.max(0, Math.min(100, percent));
        if (statusMessage && this.statusText) {
            this.statusText.textContent = statusMessage;
        }
    }
    
    setTitle(title) {
        if (this.titleText) {
            this.titleText.textContent = title;
        }
    }
    
    setAntCount(count) {
        this.numAnts = Math.max(1, count);
        if (this.stage) this.stage.innerHTML = '';
        this.ants = [];
        for (let i = 0; i < this.numAnts; i++) {
            const ant = {
                id: i,
                frameIndex: (i * 2) % this.frames.length,
                offsetPercent: (i * -6),
                element: null
            };
            
            const antImg = document.createElement('img');
            antImg.src = this.frames[ant.frameIndex];
            antImg.alt = "Walking Ant";
            antImg.className = "absolute pointer-events-none select-none transition-transform duration-100 ease-linear";
            antImg.style.width = `${this.antSize}px`;
            antImg.style.height = `${this.antSize}px`;
            antImg.style.top = `-12px`;
            antImg.style.left = `0%`;
            antImg.style.transform = `translateX(-78%)`;
            antImg.style.objectFit = 'contain';
            antImg.style.zIndex = '10';
            antImg.style.filter = "drop-shadow(0 0 3px rgba(255, 255, 255, 0.95)) drop-shadow(0 0 8px rgba(245, 158, 11, 0.6))";
            
            this.stage.appendChild(antImg);
            ant.element = antImg;
            this.ants.push(ant);
        }
        this.updatePosition();
    }
    
    destroy() {
        if (this.animationTimer) {
            clearInterval(this.animationTimer);
            this.animationTimer = null;
        }
        if (this.wrapper && this.wrapper.parentNode) {
            this.wrapper.parentNode.removeChild(this.wrapper);
        }
    }
}

// Attach globally
window.OrganixAntProgressBar = OrganixAntProgressBar;
