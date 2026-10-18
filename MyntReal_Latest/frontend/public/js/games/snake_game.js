/**
 * Game A: Snake Engine (DC Protocol Oct 2026)
 * High-performance, responsive HTML5 Canvas grid-based Snake game.
 * Zero external libraries. Full desktop keyboard + mobile touch support.
 */

class SnakeGame {
  constructor(canvas, framework) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.framework = framework;

    this.gridSize = 20; // 20x20 grid
    this.tileSize = 20; // 400x400 canvas default

    this.snake = [];
    this.direction = { x: 1, y: 0 };
    this.nextDirection = { x: 1, y: 0 };

    this.food = { x: 15, y: 10 };
    this.bonusFood = null;
    this.particles = [];

    this.isRunning = false;
    this.isPaused = false;

    // Speed configuration (significantly relaxed for smooth mobile & casual play)
    this.baseIntervalMap = {
      SLOW: 280,
      NORMAL: 200,
      FAST: 140,
      TURBO: 95
    };
    this.minFloorMap = {
      SLOW: 180,
      NORMAL: 120,
      FAST: 85,
      TURBO: 60
    };

    let savedSpeed = 'NORMAL';
    try {
      savedSpeed = localStorage.getItem('myntreal_snake_speed') || 'NORMAL';
    } catch (e) {}
    this.speedMode = this.baseIntervalMap[savedSpeed] ? savedSpeed : 'NORMAL';
    this.tickInterval = this.calcInterval();
    this.lastTickTime = 0;
    this.animFrameId = null;

    this._bindControls();
    this.resizeCanvas();
    window.addEventListener('resize', () => this.resizeCanvas());
  }

  calcInterval() {
    const base = this.baseIntervalMap[this.speedMode] || 200;
    const minFloor = this.minFloorMap[this.speedMode] || 120;
    const foodCount = Math.max(0, this.snake ? this.snake.length - 3 : 0);
    const lvl = Math.floor(foodCount / 15) + 1;
    // Gradual, gentle acceleration that never gets uncontrollably fast
    const speedUp = (lvl - 1) * 3 + (foodCount % 15) * 0.2;
    return Math.max(minFloor, base - speedUp);
  }

  setSpeedMode(mode) {
    if (this.baseIntervalMap[mode]) {
      this.speedMode = mode;
      try {
        localStorage.setItem('myntreal_snake_speed', mode);
      } catch (e) {}
      this.tickInterval = this.calcInterval();
    }
  }

  resizeCanvas() {
    if (!this.canvas || !this.canvas.parentElement) return;
    const parentWidth = this.canvas.parentElement.clientWidth;
    const maxH = Math.min(window.innerHeight * 0.42, 360);
    const size = Math.min(parentWidth - 20, maxH, 420);
    this.canvas.width = size;
    this.canvas.height = size;
    this.tileSize = size / this.gridSize;
    if (!this.isRunning) this._drawIdle();
  }

  _bindControls() {
    window.addEventListener('keydown', (e) => {
      if (!this.isRunning || this.isPaused) return;

      switch (e.code) {
        case 'ArrowUp':
        case 'KeyW':
          if (this.direction.y === 0) this.nextDirection = { x: 0, y: -1 };
          break;
        case 'ArrowDown':
        case 'KeyS':
          if (this.direction.y === 0) this.nextDirection = { x: 0, y: 1 };
          break;
        case 'ArrowLeft':
        case 'KeyA':
          if (this.direction.x === 0) this.nextDirection = { x: -1, y: 0 };
          break;
        case 'ArrowRight':
        case 'KeyD':
          if (this.direction.x === 0) this.nextDirection = { x: 1, y: 0 };
          break;
      }
    });

    // Mouse Pointer & Touch Direct Steering on Canvas
    const handlePointerSteer = (clientX, clientY) => {
      if (!this.isRunning || this.isPaused || !this.snake || this.snake.length === 0) return;
      const rect = this.canvas.getBoundingClientRect();
      const clickX = clientX - rect.left;
      const clickY = clientY - rect.top;

      // Current head center coordinates on canvas
      const head = this.snake[0];
      const headCanvasX = head.x * this.tileSize + this.tileSize / 2;
      const headCanvasY = head.y * this.tileSize + this.tileSize / 2;

      const dx = clickX - headCanvasX;
      const dy = clickY - headCanvasY;

      // Minimum deadzone threshold around head
      if (Math.hypot(dx, dy) < this.tileSize * 0.4) return;

      if (Math.abs(dx) > Math.abs(dy)) {
        if (dx > 0 && this.direction.x === 0) this.nextDirection = { x: 1, y: 0 };
        else if (dx < 0 && this.direction.x === 0) this.nextDirection = { x: -1, y: 0 };
      } else {
        if (dy > 0 && this.direction.y === 0) this.nextDirection = { x: 0, y: 1 };
        else if (dy < 0 && this.direction.y === 0) this.nextDirection = { x: 0, y: -1 };
      }
    };

    let isPointerDragging = false;
    this.canvas.addEventListener('pointerdown', (e) => {
      isPointerDragging = true;
      handlePointerSteer(e.clientX, e.clientY);
    });

    window.addEventListener('pointermove', (e) => {
      if (isPointerDragging) {
        handlePointerSteer(e.clientX, e.clientY);
      }
    });

    window.addEventListener('pointerup', () => {
      isPointerDragging = false;
    });

    // Touch swipe gesture listener on canvas
    let touchStartX = 0;
    let touchStartY = 0;
    this.canvas.addEventListener('touchstart', (e) => {
      touchStartX = e.touches[0].clientX;
      touchStartY = e.touches[0].clientY;
    }, { passive: true });

    this.canvas.addEventListener('touchend', (e) => {
      if (!this.isRunning || this.isPaused) return;
      const dx = e.changedTouches[0].clientX - touchStartX;
      const dy = e.changedTouches[0].clientY - touchStartY;
      if (Math.abs(dx) > Math.abs(dy)) {
        if (dx > 25 && this.direction.x === 0) this.nextDirection = { x: 1, y: 0 };
        else if (dx < -25 && this.direction.x === 0) this.nextDirection = { x: -1, y: 0 };
      } else {
        if (dy > 25 && this.direction.y === 0) this.nextDirection = { x: 0, y: 1 };
        else if (dy < -25 && this.direction.y === 0) this.nextDirection = { x: 0, y: -1 };
      }
    }, { passive: true });
  }

  setDirection(dirStr) {
    if (!this.isRunning || this.isPaused) return;
    if (dirStr === 'UP' && this.direction.y === 0) this.nextDirection = { x: 0, y: -1 };
    else if (dirStr === 'DOWN' && this.direction.y === 0) this.nextDirection = { x: 0, y: 1 };
    else if (dirStr === 'LEFT' && this.direction.x === 0) this.nextDirection = { x: -1, y: 0 };
    else if (dirStr === 'RIGHT' && this.direction.x === 0) this.nextDirection = { x: 1, y: 0 };
  }

  start() {
    this.reset();
    this.isRunning = true;
    this.isPaused = false;
    this.lastTickTime = performance.now();
    this._loop();
  }

  pause() {
    this.isPaused = true;
  }

  resume() {
    this.isPaused = false;
    this.lastTickTime = performance.now();
    this._loop();
  }

  reset() {
    this.isRunning = false;
    this.isPaused = false;
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }

    this.snake = [
      { x: 10, y: 10 },
      { x: 9, y: 10 },
      { x: 8, y: 10 }
    ];
    this.direction = { x: 1, y: 0 };
    this.nextDirection = { x: 1, y: 0 };
    this.tickInterval = this.calcInterval();
    this.particles = [];
    this._spawnFood();
  }

  _spawnFood() {
    let attempts = 0;
    while (attempts < 200) {
      const rx = Math.floor(Math.random() * this.gridSize);
      const ry = Math.floor(Math.random() * this.gridSize);
      const onSnake = this.snake.some(segment => segment.x === rx && segment.y === ry);
      if (!onSnake) {
        this.food = { x: rx, y: ry };
        break;
      }
      attempts++;
    }
  }

  _loop(timestamp = 0) {
    if (!this.isRunning || this.isPaused) return;

    if (timestamp - this.lastTickTime >= this.tickInterval) {
      this._update();
      this.lastTickTime = timestamp;
    }

    this._draw();
    this.animFrameId = requestAnimationFrame((t) => this._loop(t));
  }

  _update() {
    this.direction = { ...this.nextDirection };
    let newX = this.snake[0].x + this.direction.x;
    let newY = this.snake[0].y + this.direction.y;
    let wrapped = false;

    // Screen wrap-around: pass through walls to opposite side
    if (newX < 0) {
      newX = this.gridSize - 1;
      wrapped = true;
    } else if (newX >= this.gridSize) {
      newX = 0;
      wrapped = true;
    }

    if (newY < 0) {
      newY = this.gridSize - 1;
      wrapped = true;
    } else if (newY >= this.gridSize) {
      newY = 0;
      wrapped = true;
    }

    const head = { x: newX, y: newY };

    if (wrapped) {
      this._createPortalEffect(head.x * this.tileSize, head.y * this.tileSize);
    }

    // Self collision detection: only colliding with own body ends the game!
    const willEat = (head.x === this.food.x && head.y === this.food.y);
    const bodyToCheckLength = willEat ? this.snake.length : this.snake.length - 1;

    for (let i = 0; i < bodyToCheckLength; i++) {
      if (this.snake[i].x === head.x && this.snake[i].y === head.y) {
        this._handleCollision();
        return;
      }
    }

    this.snake.unshift(head);

    // Food eaten check
    if (willEat) {
      this._createParticleBurst(head.x * this.tileSize, head.y * this.tileSize, '#f59e0b');
      if (window.gameAudio) window.gameAudio.playCollect();

      this.framework.addScore(100);
      const foodCount = (this.snake.length - 3);
      this.framework.setItems(foodCount);

      // Level up every 15 foods eaten
      const lvl = Math.floor(foodCount / 15) + 1;
      const prevLvl = this.framework.level || 1;
      this.framework.setLevel(lvl);

      // Dynamically accelerate speed based on level and selected base speed
      this.tickInterval = this.calcInterval();

      // If leveled up, trigger level-up particle burst
      if (lvl > prevLvl) {
        this._createLevelUpEffect(head.x * this.tileSize, head.y * this.tileSize);
      }

      if (foodCount % 10 === 0) {
        this.framework.recordMilestone(foodCount);
      }

      this._spawnFood();
    } else {
      this.snake.pop();
    }

    // Update particle lifetimes
    for (let i = this.particles.length - 1; i >= 0; i--) {
      this.particles[i].x += this.particles[i].vx;
      this.particles[i].y += this.particles[i].vy;
      this.particles[i].alpha -= 0.05;
      if (this.particles[i].alpha <= 0) this.particles.splice(i, 1);
    }
  }

  _handleCollision() {
    this.isRunning = false;
    if (window.gameAudio) {
      if (typeof window.gameAudio.stopMusic === 'function') window.gameAudio.stopMusic();
      window.gameAudio.playCollision();
    }
    this._createParticleBurst(
      this.snake[0].x * this.tileSize,
      this.snake[0].y * this.tileSize,
      '#ef4444'
    );
    this.framework.gameOver({
      score: this.framework.score,
      itemsCollected: (this.snake.length - 3),
      level: this.framework.level
    });
  }

  _createParticleBurst(x, y, color) {
    for (let i = 0; i < 12; i++) {
      const angle = (Math.PI * 2 / 12) * i;
      const speed = Math.random() * 3 + 2;
      this.particles.push({
        x: x + this.tileSize / 2,
        y: y + this.tileSize / 2,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        alpha: 1.0,
        color: color
      });
    }
  }

  _createPortalEffect(x, y) {
    for (let i = 0; i < 6; i++) {
      const angle = (Math.PI * 2 / 6) * i;
      this.particles.push({
        x: x + this.tileSize / 2,
        y: y + this.tileSize / 2,
        vx: Math.cos(angle) * 1.5,
        vy: Math.sin(angle) * 1.5,
        alpha: 0.85,
        color: '#38bdf8'
      });
    }
  }

  _createLevelUpEffect(x, y) {
    for (let i = 0; i < 16; i++) {
      const angle = (Math.PI * 2 / 16) * i;
      const speed = Math.random() * 3 + 2;
      this.particles.push({
        x: x + this.tileSize / 2,
        y: y + this.tileSize / 2,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        alpha: 1.0,
        color: '#10b981'
      });
    }
  }

  _draw() {
    const w = this.canvas.width;
    const h = this.canvas.height;
    const ts = this.tileSize;
    const now = performance.now();

    // 1. Cybernetic 3D Arena Floor
    const bgGrad = this.ctx.createRadialGradient(w / 2, h / 2, 20, w / 2, h / 2, w * 0.72);
    bgGrad.addColorStop(0, '#0c1626');
    bgGrad.addColorStop(1, '#040711');
    this.ctx.fillStyle = bgGrad;
    this.ctx.fillRect(0, 0, w, h);

    // Subtle isometric floor grid
    this.ctx.strokeStyle = 'rgba(56, 189, 248, 0.04)';
    this.ctx.lineWidth = 1;
    for (let x = 0; x <= w; x += ts) {
      this.ctx.beginPath();
      this.ctx.moveTo(x, 0);
      this.ctx.lineTo(x, h);
      this.ctx.stroke();
    }
    for (let y = 0; y <= h; y += ts) {
      this.ctx.beginPath();
      this.ctx.moveTo(0, y);
      this.ctx.lineTo(w, y);
      this.ctx.stroke();
    }

    // 2. Draw 3D Floating Food Gem/Orb
    this._draw3DFood(ts, now);

    // 3. Draw Snake (Tail-to-Head for natural 3D depth layering)
    // 3a. Floor Shadows under all snake segments
    this._drawSnakeShadows(ts, now);

    // 3b. Continuous 3D Muscular Body with scales & specular ridges
    this._drawSnakeBody(ts, now);

    // 3c. Realistic 3D Serpent Head with eyes & flickering forked tongue
    this._draw3DHead(ts, now);

    // 4. Draw particle bursts
    this.particles.forEach(p => {
      this.ctx.fillStyle = p.color;
      this.ctx.globalAlpha = Math.max(0, p.alpha);
      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
      this.ctx.fill();
    });
    this.ctx.globalAlpha = 1.0;
  }

  _draw3DFood(ts, now) {
    const fx = this.food.x * ts + ts / 2;
    const fy = this.food.y * ts + ts / 2;
    const floatBob = Math.sin(now * 0.005) * (ts * 0.1);
    const pulse = Math.sin(now * 0.008) * 1.5;
    const radius = Math.max(4, ts * 0.38 + pulse);

    // Floor shadow
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.45)';
    this.ctx.beginPath();
    this.ctx.ellipse(fx, fy + ts * 0.32, radius * 0.9, radius * 0.45, 0, 0, Math.PI * 2);
    this.ctx.fill();

    // Outer warm glowing aura
    const auraGrad = this.ctx.createRadialGradient(fx, fy + floatBob, radius * 0.4, fx, fy + floatBob, radius * 2.2);
    auraGrad.addColorStop(0, 'rgba(245, 158, 11, 0.4)');
    auraGrad.addColorStop(1, 'rgba(245, 158, 11, 0)');
    this.ctx.fillStyle = auraGrad;
    this.ctx.beginPath();
    this.ctx.arc(fx, fy + floatBob, radius * 2.2, 0, Math.PI * 2);
    this.ctx.fill();

    // 3D Spherical Gold Energy Orb
    const orbGrad = this.ctx.createRadialGradient(
      fx - radius * 0.35,
      fy + floatBob - radius * 0.35,
      radius * 0.08,
      fx,
      fy + floatBob,
      radius
    );
    orbGrad.addColorStop(0, '#fffbeb');
    orbGrad.addColorStop(0.25, '#fde047');
    orbGrad.addColorStop(0.65, '#f59e0b');
    orbGrad.addColorStop(1, '#78350f');
    this.ctx.fillStyle = orbGrad;
    this.ctx.beginPath();
    this.ctx.arc(fx, fy + floatBob, radius, 0, Math.PI * 2);
    this.ctx.fill();

    // Specular highlight gleam
    this.ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
    this.ctx.beginPath();
    this.ctx.ellipse(
      fx - radius * 0.3,
      fy + floatBob - radius * 0.3,
      radius * 0.28,
      radius * 0.16,
      -Math.PI / 4,
      0,
      Math.PI * 2
    );
    this.ctx.fill();

    // Orbiting sparkle star
    const orbAngle = now * 0.0035;
    const sparkleX = fx + Math.cos(orbAngle) * (radius * 1.35);
    const sparkleY = fy + floatBob + Math.sin(orbAngle) * (radius * 0.85);
    this.ctx.fillStyle = '#ffffff';
    this.ctx.shadowColor = '#fbbf24';
    this.ctx.shadowBlur = 6;
    this.ctx.beginPath();
    this.ctx.arc(sparkleX, sparkleY, 1.8, 0, Math.PI * 2);
    this.ctx.fill();
    this.ctx.shadowBlur = 0;
  }

  _drawSnakeShadows(ts, now) {
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
    for (let i = this.snake.length - 1; i >= 0; i--) {
      const seg = this.snake[i];
      const cx = seg.x * ts + ts / 2 + 2;
      const cy = seg.y * ts + ts / 2 + 3.5;
      const progress = i / this.snake.length;
      const r = (ts * 0.44) * (1 - progress * 0.35);

      this.ctx.beginPath();
      this.ctx.ellipse(cx, cy, r * 1.05, r * 0.65, 0, 0, Math.PI * 2);
      this.ctx.fill();
    }
  }

  _drawSnakeBody(ts, now) {
    const total = this.snake.length;

    // Connective muscular joints (prevents broken box look during turns)
    for (let i = total - 1; i >= 1; i--) {
      const cur = this.snake[i];
      const next = this.snake[i - 1];

      // Only bridge when not wrapping around canvas boundaries
      const dx = Math.abs(cur.x - next.x);
      const dy = Math.abs(cur.y - next.y);
      if (dx <= 1 && dy <= 1) {
        const x1 = cur.x * ts + ts / 2;
        const y1 = cur.y * ts + ts / 2;
        const x2 = next.x * ts + ts / 2;
        const y2 = next.y * ts + ts / 2;

        const progress = i / total;
        const thick = (ts * 0.8) * (1 - progress * 0.35);

        this.ctx.strokeStyle = '#059669';
        this.ctx.lineWidth = thick;
        this.ctx.lineCap = 'round';
        this.ctx.beginPath();
        this.ctx.moveTo(x1, y1);
        this.ctx.lineTo(x2, y2);
        this.ctx.stroke();

        // 3D dorsal spine sheen along connection
        this.ctx.strokeStyle = 'rgba(52, 211, 153, 0.35)';
        this.ctx.lineWidth = thick * 0.35;
        this.ctx.beginPath();
        this.ctx.moveTo(x1, y1);
        this.ctx.lineTo(x2, y2);
        this.ctx.stroke();
      }
    }

    // 3D Spherical body segments with depth lighting
    for (let i = total - 1; i >= 1; i--) {
      const seg = this.snake[i];
      const cx = seg.x * ts + ts / 2;
      const cy = seg.y * ts + ts / 2;
      const progress = i / total;
      const radius = (ts * 0.45) * (1 - progress * 0.35);

      // Spherical radial gradient
      const grad = this.ctx.createRadialGradient(
        cx - radius * 0.35,
        cy - radius * 0.35,
        radius * 0.1,
        cx,
        cy,
        radius
      );
      grad.addColorStop(0, '#a7f3d0'); // Shiny highlight
      grad.addColorStop(0.25, '#10b981'); // Emerald body
      grad.addColorStop(0.7, '#047857'); // Jungle shadow
      grad.addColorStop(1, '#064e3b'); // Dark rim
      this.ctx.fillStyle = grad;

      this.ctx.beginPath();
      this.ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      this.ctx.fill();

      // Top scale ridge highlight
      this.ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
      this.ctx.beginPath();
      this.ctx.ellipse(cx - radius * 0.25, cy - radius * 0.25, radius * 0.3, radius * 0.15, -Math.PI / 4, 0, Math.PI * 2);
      this.ctx.fill();

      // Diamond scale marking along spine
      if (i % 2 === 0) {
        this.ctx.fillStyle = 'rgba(245, 158, 11, 0.65)';
        this.ctx.beginPath();
        const scR = radius * 0.35;
        this.ctx.moveTo(cx, cy - scR);
        this.ctx.lineTo(cx + scR * 0.7, cy);
        this.ctx.lineTo(cx, cy + scR);
        this.ctx.lineTo(cx - scR * 0.7, cy);
        this.ctx.closePath();
        this.ctx.fill();
      }
    }
  }

  _draw3DHead(ts, now) {
    const head = this.snake[0];
    const cx = head.x * ts + ts / 2;
    const cy = head.y * ts + ts / 2;

    let angle = 0;
    if (this.direction.x === 1) angle = 0;
    else if (this.direction.x === -1) angle = Math.PI;
    else if (this.direction.y === 1) angle = Math.PI / 2;
    else if (this.direction.y === -1) angle = -Math.PI / 2;

    this.ctx.save();
    this.ctx.translate(cx, cy);
    this.ctx.rotate(angle);

    const headR = ts * 0.48;

    // Animated Flickering Forked Red Tongue
    const tongueCycle = Math.sin(now * 0.015);
    if (tongueCycle > 0.15) {
      const tongueExtension = (ts * 0.55) * Math.min(1, (tongueCycle - 0.15) / 0.5);
      const txStart = headR * 0.95;
      const txEnd = txStart + tongueExtension;

      this.ctx.strokeStyle = '#ef4444';
      this.ctx.lineWidth = 2;
      this.ctx.lineCap = 'round';
      this.ctx.beginPath();
      this.ctx.moveTo(txStart, 0);
      this.ctx.lineTo(txEnd, 0);
      this.ctx.lineTo(txEnd + 4, -3);
      this.ctx.moveTo(txEnd, 0);
      this.ctx.lineTo(txEnd + 4, 3);
      this.ctx.stroke();
    }

    // 3D Organic Serpent Head Geometry (tapered wedge)
    this.ctx.beginPath();
    this.ctx.moveTo(headR * 1.15, 0);
    this.ctx.bezierCurveTo(headR * 1.1, headR * 0.65, headR * 0.3, headR * 0.85, -headR * 0.7, headR * 0.6);
    this.ctx.bezierCurveTo(-headR * 0.95, headR * 0.35, -headR * 0.95, -headR * 0.35, -headR * 0.7, -headR * 0.6);
    this.ctx.bezierCurveTo(headR * 0.3, -headR * 0.85, headR * 1.1, -headR * 0.65, headR * 1.15, 0);
    this.ctx.closePath();

    const headGrad = this.ctx.createRadialGradient(-headR * 0.1, -headR * 0.2, headR * 0.1, 0, 0, headR * 1.2);
    headGrad.addColorStop(0, '#a7f3d0');
    headGrad.addColorStop(0.3, '#10b981');
    headGrad.addColorStop(0.75, '#059669');
    headGrad.addColorStop(1, '#022c22');
    this.ctx.fillStyle = headGrad;
    this.ctx.fill();

    this.ctx.strokeStyle = 'rgba(110, 231, 183, 0.45)';
    this.ctx.lineWidth = 1.2;
    this.ctx.stroke();

    // Nostrils
    this.ctx.fillStyle = '#064e3b';
    this.ctx.beginPath();
    this.ctx.arc(headR * 0.88, -headR * 0.2, 1.2, 0, Math.PI * 2);
    this.ctx.arc(headR * 0.88, headR * 0.2, 1.2, 0, Math.PI * 2);
    this.ctx.fill();

    // 3D Viper Eyes with Vertical Slit Pupils
    const eyeOffsetX = headR * 0.25;
    const eyeOffsetY = headR * 0.52;
    const eyeR = headR * 0.26;

    [-1, 1].forEach(side => {
      const ey = eyeOffsetY * side;

      // Socket ridge
      this.ctx.fillStyle = '#064e3b';
      this.ctx.beginPath();
      this.ctx.arc(eyeOffsetX, ey, eyeR + 1.2, 0, Math.PI * 2);
      this.ctx.fill();

      // Golden Iris
      const eyeGrad = this.ctx.createRadialGradient(eyeOffsetX - 1, ey - 1, 0.5, eyeOffsetX, ey, eyeR);
      eyeGrad.addColorStop(0, '#fef08a');
      eyeGrad.addColorStop(0.6, '#f59e0b');
      eyeGrad.addColorStop(1, '#b45309');
      this.ctx.fillStyle = eyeGrad;
      this.ctx.beginPath();
      this.ctx.arc(eyeOffsetX, ey, eyeR, 0, Math.PI * 2);
      this.ctx.fill();

      // Slit Pupil
      this.ctx.fillStyle = '#090e17';
      this.ctx.beginPath();
      this.ctx.ellipse(eyeOffsetX + 0.5, ey, eyeR * 0.35, eyeR * 0.88, 0, 0, Math.PI * 2);
      this.ctx.fill();

      // Glossy Reflection Highlight
      this.ctx.fillStyle = '#ffffff';
      this.ctx.beginPath();
      this.ctx.arc(eyeOffsetX - 1, ey - 1.5 * side, 1.2, 0, Math.PI * 2);
      this.ctx.fill();
    });

    // Golden Cobra Crest Marking
    this.ctx.fillStyle = 'rgba(245, 158, 11, 0.8)';
    this.ctx.beginPath();
    this.ctx.moveTo(headR * 0.4, 0);
    this.ctx.lineTo(-headR * 0.1, headR * 0.3);
    this.ctx.lineTo(-headR * 0.35, 0);
    this.ctx.lineTo(-headR * 0.1, -headR * 0.3);
    this.ctx.closePath();
    this.ctx.fill();

    this.ctx.restore();
  }

  _drawIdle() {
    const w = this.canvas.width;
    const h = this.canvas.height;
    const bgGrad = this.ctx.createRadialGradient(w / 2, h / 2, 20, w / 2, h / 2, w * 0.72);
    bgGrad.addColorStop(0, '#0c1626');
    bgGrad.addColorStop(1, '#040711');
    this.ctx.fillStyle = bgGrad;
    this.ctx.fillRect(0, 0, w, h);

    this.ctx.fillStyle = '#94a3b8';
    this.ctx.font = '600 14px "Plus Jakarta Sans", sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.fillText('Click "Start Game" to enter 3D Arcade', w / 2, h / 2);
  }
}
