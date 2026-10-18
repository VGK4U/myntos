/**
 * Game D: Bubble Blaster / Bubble Shooter 3D Engine (DC Protocol Oct 2026)
 * Hexagonal staggered grid, realistic trajectory with wall reflections,
 * glossy 3D marble bubbles, match-3 pops, hanging cluster drops,
 * bubble swapping, and descending ceiling pressure.
 */

class BubbleBlasterGame {
  constructor(canvas, framework) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.framework = framework;

    this.cols = 8;
    this.maxRows = 12;
    this.bubbleRadius = 20;
    this.rowHeight = 34; // r * sqrt(3)

    // Vibrant 3D Candy Marble Palette
    this.COLORS = [
      { id: 'CYAN', main: '#06b6d4', dark: '#0e7490', light: '#a5f3fc' },
      { id: 'MAGENTA', main: '#d946ef', dark: '#a21caf', light: '#f5d0fe' },
      { id: 'RED', main: '#ef4444', dark: '#b91c1c', light: '#fca5a5' },
      { id: 'GREEN', main: '#10b981', dark: '#047857', light: '#a7f3d0' },
      { id: 'GOLD', main: '#f59e0b', dark: '#b45309', light: '#fde68a' },
      { id: 'VIOLET', main: '#8b5cf6', dark: '#6d28d9', light: '#ddd6fe' }
    ];

    this.grid = []; // 2D array of bubbles
    this.activeBubble = null;
    this.nextBubble = null;
    this.flyingBubble = null;

    this.cannonX = 0;
    this.cannonY = 0;
    this.aimAngle = -Math.PI / 2; // Point straight up
    this.isAiming = false;

    this.misses = 0;
    this.maxMisses = 5; // Drops ceiling every 5 non-popping shots
    this.ceilingOffset = 0;

    this.particles = [];
    this.droppingBubbles = [];

    this.isRunning = false;
    this.isPaused = false;
    this.animFrameId = null;

    this.speedMode = 'NORMAL';
    this.projectileSpeed = 18;

    this._bindControls();
    this.resizeCanvas();
    window.addEventListener('resize', () => this.resizeCanvas());
  }

  setSpeedMode(mode) {
    this.speedMode = mode;
    if (mode === 'SLOW') {
      this.projectileSpeed = 13;
    } else if (mode === 'FAST') {
      this.projectileSpeed = 23;
    } else if (mode === 'TURBO') {
      this.projectileSpeed = 28;
    } else {
      this.projectileSpeed = 18;
    }
  }

  resizeCanvas() {
    if (!this.canvas || !this.canvas.parentElement) return;
    const parentWidth = this.canvas.parentElement.clientWidth;
    const w = Math.min(parentWidth - 16, 420);
    const h = Math.min(window.innerHeight * 0.44, 480);

    this.canvas.width = w;
    this.canvas.height = h;

    this.bubbleRadius = w / (this.cols * 2);
    this.rowHeight = this.bubbleRadius * Math.sqrt(3);

    this.cannonX = w / 2;
    this.cannonY = h - 35;

    if (!this.isRunning) this._drawIdle();
  }

  _bindControls() {
    // Mouse & Touch aiming
    const updateAimFromCoords = (clientX, clientY) => {
      const rect = this.canvas.getBoundingClientRect();
      const scaleX = this.canvas.width / rect.width;
      const scaleY = this.canvas.height / rect.height;
      const targetX = (clientX - rect.left) * scaleX;
      const targetY = (clientY - rect.top) * scaleY;

      const dx = targetX - this.cannonX;
      const dy = targetY - this.cannonY;

      let angle = Math.atan2(dy, dx);
      // Clamp angle: cannot shoot downwards
      const minAngle = -Math.PI + 0.18;
      const maxAngle = -0.18;
      angle = Math.max(minAngle, Math.min(maxAngle, angle));

      this.aimAngle = angle;
    };

    this.canvas.addEventListener('pointermove', (e) => {
      if (!this.isRunning || this.isPaused) return;
      updateAimFromCoords(e.clientX, e.clientY);
    });

    this.canvas.addEventListener('pointerdown', (e) => {
      if (!this.isRunning || this.isPaused) return;
      if (e.button === 2) {
        // Right click swaps bubbles
        this.swapBubbles();
        return;
      }
      this.isAiming = true;
      updateAimFromCoords(e.clientX, e.clientY);
    });

    this.canvas.addEventListener('pointerup', (e) => {
      if (!this.isRunning || this.isPaused) return;
      if (this.isAiming) {
        this.isAiming = false;
        this.shoot();
      }
    });

    window.addEventListener('keydown', (e) => {
      if (!this.isRunning || this.isPaused) return;
      if (e.code === 'Space' || e.code === 'KeyC') {
        this.swapBubbles();
      } else if (e.code === 'ArrowLeft') {
        this.aimAngle = Math.max(-Math.PI + 0.18, this.aimAngle - 0.08);
      } else if (e.code === 'ArrowRight') {
        this.aimAngle = Math.min(-0.18, this.aimAngle + 0.08);
      } else if (e.code === 'ArrowUp') {
        this.shoot();
      }
    });

    this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());
  }

  _getRandomColor() {
    // Bias towards existing colors on board so games remain solvably matchable
    const existing = new Set();
    for (let r = 0; r < this.grid.length; r++) {
      for (let c = 0; c < this.grid[r].length; c++) {
        if (this.grid[r][c]) existing.add(this.grid[r][c].id);
      }
    }

    let pool = this.COLORS;
    if (existing.size > 0) {
      pool = this.COLORS.filter(col => existing.has(col.id));
      if (pool.length === 0) pool = this.COLORS;
    }

    return pool[Math.floor(Math.random() * pool.length)];
  }

  start() {
    this.reset();
    this.isRunning = true;
    this.isPaused = false;
    this._initBoard();
    this._loop();
  }

  pause() {
    this.isPaused = true;
  }

  resume() {
    this.isPaused = false;
    this._loop();
  }

  reset() {
    this.isRunning = false;
    this.isPaused = false;
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }

    this.grid = [];
    this.flyingBubble = null;
    this.activeBubble = null;
    this.nextBubble = null;
    this.misses = 0;
    this.ceilingOffset = 0;
    this.particles = [];
    this.droppingBubbles = [];
  }

  _initBoard() {
    this.grid = [];
    // Start with 5 rows of colorful bubbles
    const initialRows = 5;
    for (let r = 0; r < initialRows; r++) {
      const isOdd = r % 2 === 1;
      const rowCols = isOdd ? this.cols - 1 : this.cols;
      const row = [];
      for (let c = 0; c < rowCols; c++) {
        row.push(this.COLORS[Math.floor(Math.random() * this.COLORS.length)]);
      }
      this.grid.push(row);
    }

    this.activeBubble = this._getRandomColor();
    this.nextBubble = this._getRandomColor();
  }

  swapBubbles() {
    if (this.flyingBubble || !this.activeBubble || !this.nextBubble) return;
    const temp = this.activeBubble;
    this.activeBubble = this.nextBubble;
    this.nextBubble = temp;
    if (window.gameAudio) window.gameAudio.playRotate();
  }

  shoot() {
    if (this.flyingBubble || !this.activeBubble || !this.isRunning || this.isPaused) return;

    const speed = this.projectileSpeed || 18;
    this.flyingBubble = {
      x: this.cannonX,
      y: this.cannonY,
      vx: Math.cos(this.aimAngle) * speed,
      vy: Math.sin(this.aimAngle) * speed,
      color: this.activeBubble,
      radius: this.bubbleRadius
    };

    this.activeBubble = this.nextBubble;
    this.nextBubble = this._getRandomColor();

    if (window.gameAudio) window.gameAudio.playBubbleShoot();
  }

  _loop() {
    if (!this.isRunning || this.isPaused) return;

    try {
      this._update();
      this._draw();
    } catch (err) {
      console.error('[BubbleBlaster] Loop error:', err);
    }

    this.animFrameId = requestAnimationFrame(() => this._loop());
  }

  _update() {
    // 1. Update Flying Bubble Physics
    if (this.flyingBubble) {
      const b = this.flyingBubble;
      b.x += b.vx;
      b.y += b.vy;

      // Wall reflections (left and right)
      if (b.x - b.radius <= 0) {
        b.x = b.radius;
        b.vx = -b.vx;
      } else if (b.x + b.radius >= this.canvas.width) {
        b.x = this.canvas.width - b.radius;
        b.vx = -b.vx;
      }

      // Check collision with ceiling or other bubbles
      let collided = false;
      if (b.y - b.radius <= this.ceilingOffset) {
        collided = true;
      } else {
        // Check collision against all placed bubbles
        for (let r = 0; r < this.grid.length; r++) {
          for (let c = 0; c < this.grid[r].length; c++) {
            if (this.grid[r][c]) {
              const pos = this._getBubbleCoords(r, c);
              const dx = b.x - pos.x;
              const dy = b.y - pos.y;
              const distSq = dx * dx + dy * dy;
              if (distSq <= Math.pow(b.radius + this.bubbleRadius - 3, 2)) {
                collided = true;
                break;
              }
            }
          }
          if (collided) break;
        }
      }

      if (collided) {
        try {
          this._snapAndResolve(b);
        } catch (e) {
          console.error('[BubbleBlaster] Snap error:', e);
        } finally {
          this.flyingBubble = null;
        }
      } else if (b.y > this.canvas.height + 40 || b.y < -60 || b.x < -60 || b.x > this.canvas.width + 60) {
        this.flyingBubble = null;
      }
    }

    // 2. Update Dropping (Falling) Bubbles
    for (let i = this.droppingBubbles.length - 1; i >= 0; i--) {
      const db = this.droppingBubbles[i];
      db.vy += 0.8;
      db.x += db.vx;
      db.y += db.vy;
      db.rotation += db.vRot;

      if (db.y > this.canvas.height + 40) {
        this.droppingBubbles.splice(i, 1);
      }
    }

    // 3. Update Sparkle / Burst Particles
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.x += p.vx;
      p.y += p.vy;
      p.vy += 0.15;
      p.alpha -= 0.025;
      if (p.alpha <= 0) {
        this.particles.splice(i, 1);
      }
    }
  }

  _getBubbleCoords(r, c) {
    const isOdd = r % 2 === 1;
    const startX = isOdd ? this.bubbleRadius * 2 : this.bubbleRadius;
    const x = startX + c * (this.bubbleRadius * 2);
    const y = this.ceilingOffset + this.bubbleRadius + r * this.rowHeight;
    return { x, y };
  }

  _snapAndResolve(b) {
    // Find closest open grid slot
    let bestR = 0;
    let bestC = 0;
    let minDistSq = Infinity;

    // Check rows up to grid.length + 1
    const searchRows = Math.min(this.maxRows, this.grid.length + 2);
    for (let r = 0; r < searchRows; r++) {
      const isOdd = r % 2 === 1;
      const rowCols = isOdd ? this.cols - 1 : this.cols;
      for (let c = 0; c < rowCols; c++) {
        // Ensure row exists
        while (this.grid.length <= r) {
          const oddR = this.grid.length % 2 === 1;
          this.grid.push(Array(oddR ? this.cols - 1 : this.cols).fill(null));
        }

        if (!this.grid[r][c]) {
          const pos = this._getBubbleCoords(r, c);
          const dx = b.x - pos.x;
          const dy = b.y - pos.y;
          const distSq = dx * dx + dy * dy;
          if (distSq < minDistSq) {
            minDistSq = distSq;
            bestR = r;
            bestC = c;
          }
        }
      }
    }

    // Place bubble into the chosen slot
    this.grid[bestR][bestC] = b.color;

    // 4. Find Match-3 cluster using BFS
    const matches = this._findMatches(bestR, bestC, b.color.id);

    if (matches.length >= 3) {
      // Pop matching cluster!
      matches.forEach(m => {
        const pos = this._getBubbleCoords(m.r, m.c);
        this._spawnBurstParticles(pos.x, pos.y, this.grid[m.r][m.c].main);
        this.grid[m.r][m.c] = null;
      });

      const pts = matches.length * 100;
      if (this.framework && typeof this.framework.addScore === 'function') this.framework.addScore(pts);
      if (this.framework && typeof this.framework.addItemsCollected === 'function') this.framework.addItemsCollected(matches.length);
      if (window.gameAudio) window.gameAudio.playBubblePop(1.0 + (matches.length * 0.1));

      // Check for disconnected hanging clusters
      this._dropFloatingClusters();

      // Check Level Clear (all bubbles popped)
      let remainingBubbles = 0;
      for (let r = 0; r < this.grid.length; r++) {
        for (let c = 0; c < this.grid[r].length; c++) {
          if (this.grid[r][c]) remainingBubbles++;
        }
      }
      if (remainingBubbles === 0) {
        if (this.framework && typeof this.framework.setLevel === 'function') {
          this.framework.setLevel((this.framework.level || 1) + 1);
        }
        if (this.framework && typeof this.framework.addScore === 'function') {
          this.framework.addScore(1500);
        }
        if (window.gameAudio && typeof window.gameAudio.playPowerup === 'function') {
          window.gameAudio.playPowerup();
        }
        this.ceilingOffset = 0;
        this.misses = 0;
        this._initBoard();
        return;
      }
    } else {
      // Non-matching shot adds to miss pressure
      this.misses++;
      if (this.misses >= this.maxMisses) {
        this.misses = 0;
        this._pushCeilingDown();
      }
    }

    // 5. Check Game Over (bubble crossed danger floor line)
    this._checkGameOver();
  }

  _getNeighbors(r, c) {
    const isOdd = r % 2 === 1;
    // Hexagonal neighbor offsets
    const offsets = isOdd ? [
      { r: -1, c: 0 }, { r: -1, c: 1 },
      { r: 0, c: -1 }, { r: 0, c: 1 },
      { r: 1, c: 0 }, { r: 1, c: 1 }
    ] : [
      { r: -1, c: -1 }, { r: -1, c: 0 },
      { r: 0, c: -1 }, { r: 0, c: 1 },
      { r: 1, c: -1 }, { r: 1, c: 0 }
    ];

    const neighbors = [];
    offsets.forEach(off => {
      const nr = r + off.r;
      const nc = c + off.c;
      if (nr >= 0 && nr < this.grid.length) {
        const rowCols = nr % 2 === 1 ? this.cols - 1 : this.cols;
        if (nc >= 0 && nc < rowCols) {
          neighbors.push({ r: nr, c: nc });
        }
      }
    });
    return neighbors;
  }

  _findMatches(startR, startC, targetColorId) {
    const matches = [];
    const queue = [{ r: startR, c: startC }];
    const visited = new Set([`${startR},${startC}`]);

    while (queue.length > 0) {
      const cur = queue.shift();
      matches.push(cur);

      const neighbors = this._getNeighbors(cur.r, cur.c);
      neighbors.forEach(n => {
        const key = `${n.r},${n.c}`;
        if (!visited.has(key) && this.grid[n.r][n.c] && this.grid[n.r][n.c].id === targetColorId) {
          visited.add(key);
          queue.push(n);
        }
      });
    }

    return matches;
  }

  _dropFloatingClusters() {
    // Find all bubbles connected to the top row (r === 0)
    const connected = new Set();
    const queue = [];

    if (this.grid.length > 0) {
      for (let c = 0; c < this.grid[0].length; c++) {
        if (this.grid[0][c]) {
          connected.add(`0,${c}`);
          queue.push({ r: 0, c });
        }
      }
    }

    while (queue.length > 0) {
      const cur = queue.shift();
      const neighbors = this._getNeighbors(cur.r, cur.c);
      neighbors.forEach(n => {
        const key = `${n.r},${n.c}`;
        if (!connected.has(key) && this.grid[n.r][n.c]) {
          connected.add(key);
          queue.push(n);
        }
      });
    }

    // Any bubble NOT in connected is hanging: drop it!
    let droppedCount = 0;
    for (let r = 0; r < this.grid.length; r++) {
      for (let c = 0; c < this.grid[r].length; c++) {
        if (this.grid[r][c] && !connected.has(`${r},${c}`)) {
          const pos = this._getBubbleCoords(r, c);
          this.droppingBubbles.push({
            x: pos.x,
            y: pos.y,
            vx: (Math.random() - 0.5) * 4,
            vy: -(Math.random() * 3 + 2),
            vRot: (Math.random() - 0.5) * 0.2,
            rotation: 0,
            color: this.grid[r][c],
            radius: this.bubbleRadius
          });
          this.grid[r][c] = null;
          droppedCount++;
        }
      }
    }

    if (droppedCount > 0) {
      const bonus = droppedCount * 250;
      if (this.framework && typeof this.framework.addScore === 'function') this.framework.addScore(bonus);
      if (this.framework && typeof this.framework.addItemsCollected === 'function') this.framework.addItemsCollected(droppedCount);
      if (window.gameAudio) window.gameAudio.playClusterDrop();
    }
  }

  _pushCeilingDown() {
    this.ceilingOffset += this.rowHeight * 0.75;
    if (window.gameAudio && typeof window.gameAudio.playDrop === 'function') {
      window.gameAudio.playDrop();
    }
  }

  _checkGameOver() {
    const dangerY = this.canvas.height - 68;
    for (let r = 0; r < this.grid.length; r++) {
      for (let c = 0; c < this.grid[r].length; c++) {
        if (this.grid[r][c]) {
          const pos = this._getBubbleCoords(r, c);
          if (pos.y + this.bubbleRadius >= dangerY) {
            this._handleGameOver();
            return;
          }
        }
      }
    }
  }

  _handleGameOver() {
    this.isRunning = false;
    if (window.gameAudio) {
      if (typeof window.gameAudio.playGameOver === 'function') window.gameAudio.playGameOver();
      if (typeof window.gameAudio.stopMusic === 'function') window.gameAudio.stopMusic();
    }
    this.framework.gameOver({
      score: this.framework.score,
      itemsCollected: this.framework.itemsCollected,
      level: this.framework.level
    });
  }

  _spawnBurstParticles(x, y, color) {
    for (let i = 0; i < 12; i++) {
      const angle = (Math.PI * 2 / 12) * i + Math.random() * 0.3;
      const speed = Math.random() * 4 + 2;
      this.particles.push({
        x,
        y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        radius: Math.random() * 3 + 2,
        color,
        alpha: 1.0
      });
    }
  }

  _draw() {
    const w = this.canvas.width;
    const h = this.canvas.height;

    // 1. Cyber 3D Arcade Arena Background
    const bgGrad = this.ctx.createRadialGradient(w / 2, h / 2, 20, w / 2, h / 2, w * 0.85);
    bgGrad.addColorStop(0, '#0f172a');
    bgGrad.addColorStop(1, '#030712');
    this.ctx.fillStyle = bgGrad;
    this.ctx.fillRect(0, 0, w, h);

    // Subtle Hexagonal grid wireframe
    this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
    this.ctx.lineWidth = 1;
    for (let y = 0; y < h; y += 40) {
      this.ctx.beginPath();
      this.ctx.moveTo(0, y);
      this.ctx.lineTo(w, y);
      this.ctx.stroke();
    }

    // 2. Danger Threshold Floor Line
    const dangerY = h - 68;
    this.ctx.strokeStyle = 'rgba(239, 68, 68, 0.45)';
    this.ctx.setLineDash([6, 6]);
    this.ctx.lineWidth = 2;
    this.ctx.beginPath();
    this.ctx.moveTo(0, dangerY);
    this.ctx.lineTo(w, dangerY);
    this.ctx.stroke();
    this.ctx.setLineDash([]);

    // 3. Aiming Trajectory Dots with Wall Reflections
    if (!this.flyingBubble && this.activeBubble) {
      this._drawTrajectory(w, h);
    }

    // 4. Draw Settled Grid Bubbles (3D Glossy Marbles)
    for (let r = 0; r < this.grid.length; r++) {
      for (let c = 0; c < this.grid[r].length; c++) {
        if (this.grid[r][c]) {
          const pos = this._getBubbleCoords(r, c);
          this._draw3DBubble(pos.x, pos.y, this.bubbleRadius, this.grid[r][c]);
        }
      }
    }

    // 5. Draw Dropping Bubbles
    this.droppingBubbles.forEach(db => {
      this._draw3DBubble(db.x, db.y, db.radius, db.color);
    });

    // 6. Draw Flying Bubble
    if (this.flyingBubble) {
      this._draw3DBubble(
        this.flyingBubble.x,
        this.flyingBubble.y,
        this.flyingBubble.radius,
        this.flyingBubble.color
      );
    }

    // 7. Draw Cannon & Next Bubble Cradle
    this._drawCannon(w, h);

    // 8. Draw Particles
    this.particles.forEach(p => {
      this.ctx.fillStyle = p.color;
      this.ctx.globalAlpha = p.alpha;
      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      this.ctx.fill();
    });
    this.ctx.globalAlpha = 1.0;
  }

  _drawTrajectory(w, h) {
    const startX = this.cannonX;
    const startY = this.cannonY;
    let curX = startX;
    let curY = startY;
    let vx = Math.cos(this.aimAngle);
    let vy = Math.sin(this.aimAngle);
    const step = 14;

    this.ctx.fillStyle = 'rgba(255, 255, 255, 0.65)';
    for (let i = 0; i < 28; i++) {
      curX += vx * step;
      curY += vy * step;

      // Bounce off walls
      if (curX <= this.bubbleRadius) {
        curX = this.bubbleRadius;
        vx = -vx;
      } else if (curX >= w - this.bubbleRadius) {
        curX = w - this.bubbleRadius;
        vx = -vx;
      }

      if (curY <= this.ceilingOffset + this.bubbleRadius) break;

      const dotSize = Math.max(2, 4.5 - (i * 0.1));
      this.ctx.beginPath();
      this.ctx.arc(curX, curY, dotSize, 0, Math.PI * 2);
      this.ctx.fill();
    }
  }

  _draw3DBubble(x, y, r, colorObj) {
    if (!colorObj) return;
    const col = colorObj.main || '#06b6d4';
    const dark = colorObj.dark || '#0e7490';
    const light = colorObj.light || '#a5f3fc';

    // Floor drop shadow for 3D depth
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.35)';
    this.ctx.beginPath();
    this.ctx.ellipse(x, y + r * 0.7, r * 0.85, r * 0.35, 0, 0, Math.PI * 2);
    this.ctx.fill();

    // 3D Spherical Radial Depth Gradient
    const grad = this.ctx.createRadialGradient(
      x - r * 0.35,
      y - r * 0.35,
      r * 0.08,
      x,
      y,
      r
    );
    grad.addColorStop(0, '#ffffff');
    grad.addColorStop(0.25, light);
    grad.addColorStop(0.70, col);
    grad.addColorStop(1, dark);

    this.ctx.fillStyle = grad;
    this.ctx.beginPath();
    this.ctx.arc(x, y, r - 0.5, 0, Math.PI * 2);
    this.ctx.fill();

    // Specular Highlight (Crisp White Gleam in top-left)
    this.ctx.fillStyle = 'rgba(255, 255, 255, 0.85)';
    this.ctx.beginPath();
    this.ctx.ellipse(
      x - r * 0.36,
      y - r * 0.36,
      r * 0.28,
      r * 0.16,
      -Math.PI / 4,
      0,
      Math.PI * 2
    );
    this.ctx.fill();

    // Secondary subtle bottom-right bounce rim light
    this.ctx.fillStyle = 'rgba(255, 255, 255, 0.22)';
    this.ctx.beginPath();
    this.ctx.ellipse(
      x + r * 0.35,
      y + r * 0.35,
      r * 0.22,
      r * 0.10,
      -Math.PI / 4,
      0,
      Math.PI * 2
    );
    this.ctx.fill();
  }

  _drawCannon(w, h) {
    const cx = this.cannonX;
    const cy = this.cannonY;

    // Aiming Directional Needle / Turret Base
    this.ctx.save();
    this.ctx.translate(cx, cy);
    this.ctx.rotate(this.aimAngle + Math.PI / 2);

    // Metallic Cannon Barrel
    const barrelGrad = this.ctx.createLinearGradient(-10, -40, 10, 0);
    barrelGrad.addColorStop(0, '#94a3b8');
    barrelGrad.addColorStop(0.5, '#475569');
    barrelGrad.addColorStop(1, '#1e293b');
    this.ctx.fillStyle = barrelGrad;
    this.ctx.beginPath();
    this.ctx.roundRect(-8, -36, 16, 28, 4);
    this.ctx.fill();
    this.ctx.restore();

    // Cannon Circular Pedestal
    const pedestalGrad = this.ctx.createRadialGradient(cx, cy, 4, cx, cy, 26);
    pedestalGrad.addColorStop(0, '#334155');
    pedestalGrad.addColorStop(1, '#0f172a');
    this.ctx.fillStyle = pedestalGrad;
    this.ctx.beginPath();
    this.ctx.arc(cx, cy, 24, 0, Math.PI * 2);
    this.ctx.fill();

    this.ctx.strokeStyle = '#38bdf8';
    this.ctx.lineWidth = 2;
    this.ctx.stroke();

    // Active loaded bubble inside cannon
    if (this.activeBubble && !this.flyingBubble) {
      this._draw3DBubble(cx, cy, this.bubbleRadius, this.activeBubble);
    }

    // NEXT Bubble Cradle (beside cannon on the left)
    const nextX = cx - 55;
    const nextY = cy;

    this.ctx.fillStyle = 'rgba(15, 23, 42, 0.8)';
    this.ctx.beginPath();
    this.ctx.arc(nextX, nextY, 18, 0, Math.PI * 2);
    this.ctx.fill();
    this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
    this.ctx.lineWidth = 1;
    this.ctx.stroke();

    if (this.nextBubble) {
      this._draw3DBubble(nextX, nextY, this.bubbleRadius * 0.72, this.nextBubble);
    }

    // Swap Hint Label
    this.ctx.fillStyle = '#94a3b8';
    this.ctx.font = '700 9px "Plus Jakarta Sans", sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.fillText('NEXT', nextX, nextY + 28);
  }

  _drawIdle() {
    const w = this.canvas.width;
    const h = this.canvas.height;
    this.ctx.fillStyle = '#0f172a';
    this.ctx.fillRect(0, 0, w, h);

    this.ctx.fillStyle = '#94a3b8';
    this.ctx.font = '600 13px "Plus Jakarta Sans", sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.fillText('Press "Start Game" or Tap to Aim & Shoot', w / 2, h / 2);
  }
}
