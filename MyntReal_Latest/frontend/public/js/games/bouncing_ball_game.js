/**
 * Game E: Bouncing Ball / Brick Breaker 3D Engine (DC Protocol Oct 2026)
 * Glowing 3D futuristic paddle, chrome sphere with motion trails,
 * colorful beveled 3D multi-hit bricks, dynamic angle physics,
 * falling powerups (Multiball, Wide Paddle, Fireball, Slow-mo, Extra Life).
 */

class BouncingBallGame {
  constructor(canvas, framework) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.framework = framework;

    this.paddleW = 86;
    this.paddleH = 14;
    this.paddleX = 0;
    this.paddleY = 0;
    this.paddleVx = 0;

    this.balls = [];
    this.bricks = [];
    this.powerups = [];
    this.particles = [];

    this.lives = 3;
    this.combo = 0;
    this.isFireballActive = false;
    this.fireballTimer = null;
    this.widePaddleTimer = null;

    // Ball speed settings
    this.speedMode = 'NORMAL';
    this.ballBaseSpeed = 4.8;

    this.isRunning = false;
    this.isPaused = false;
    this.animFrameId = null;

    this._bindControls();
    this.resizeCanvas();
    window.addEventListener('resize', () => this.resizeCanvas());
  }

  setSpeedMode(mode) {
    this.speedMode = mode;
    if (mode === 'SLOW') {
      this.ballBaseSpeed = 3.4;
    } else if (mode === 'FAST') {
      this.ballBaseSpeed = 6.2;
    } else if (mode === 'TURBO') {
      this.ballBaseSpeed = 7.8;
    } else { // NORMAL
      this.ballBaseSpeed = 4.8;
    }

    // Apply speed scaling to active balls
    this.balls.forEach(b => {
      if (!b.isAttached) {
        const curSpd = Math.hypot(b.vx, b.vy);
        if (curSpd > 0.1) {
          b.vx = (b.vx / curSpd) * this.ballBaseSpeed;
          b.vy = (b.vy / curSpd) * this.ballBaseSpeed;
        }
      }
    });
  }

  resizeCanvas() {
    if (!this.canvas || !this.canvas.parentElement) return;
    const parentWidth = this.canvas.parentElement.clientWidth;
    const w = Math.min(parentWidth - 16, 460);
    const h = Math.min(window.innerHeight * 0.44, 480);

    this.canvas.width = w;
    this.canvas.height = h;

    this.paddleY = h - 28;
    this.paddleX = (w - this.paddleW) / 2;

    if (!this.isRunning) this._drawIdle();
  }

  _bindControls() {
    // Mouse & Touch movement
    const movePaddleTo = (clientX) => {
      const rect = this.canvas.getBoundingClientRect();
      const scaleX = this.canvas.width / rect.width;
      const targetX = (clientX - rect.left) * scaleX - this.paddleW / 2;
      this.paddleX = Math.max(4, Math.min(this.canvas.width - this.paddleW - 4, targetX));
    };

    this.canvas.addEventListener('pointermove', (e) => {
      if (!this.isRunning || this.isPaused) return;
      movePaddleTo(e.clientX);
    });

    this.canvas.addEventListener('pointerdown', (e) => {
      if (!this.isRunning || this.isPaused) return;
      movePaddleTo(e.clientX);
      // Launch ball if stationary
      this._launchStationaryBall();
    });

    window.addEventListener('keydown', (e) => {
      if (!this.isRunning || this.isPaused) return;
      if (e.code === 'ArrowLeft' || e.code === 'KeyA') {
        this.paddleX = Math.max(4, this.paddleX - 24);
      } else if (e.code === 'ArrowRight' || e.code === 'KeyD') {
        this.paddleX = Math.min(this.canvas.width - this.paddleW - 4, this.paddleX + 24);
      } else if (e.code === 'Space') {
        this._launchStationaryBall();
      }
    });

    this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());
  }

  moveLeft() {
    this.paddleX = Math.max(4, this.paddleX - 26);
  }

  moveRight() {
    this.paddleX = Math.min(this.canvas.width - this.paddleW - 4, this.paddleX + 26);
  }

  _launchStationaryBall() {
    this.balls.forEach(b => {
      if (b.isAttached) {
        b.isAttached = false;
        const spd = this.ballBaseSpeed || 4.8;
        b.vx = (Math.random() - 0.5) * (spd * 0.6);
        b.vy = -spd;
      }
    });
  }

  start() {
    this.reset();
    this.isRunning = true;
    this.isPaused = false;
    this._initLevel();
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

    if (this.fireballTimer) clearTimeout(this.fireballTimer);
    if (this.widePaddleTimer) clearTimeout(this.widePaddleTimer);

    this.paddleW = 86;
    this.paddleX = (this.canvas.width - this.paddleW) / 2;
    this.lives = 3;
    this.combo = 0;
    this.isFireballActive = false;

    this.balls = [];
    this.bricks = [];
    this.powerups = [];
    this.particles = [];
  }

  _initLevel() {
    this.paddleW = 86;
    this.paddleX = (this.canvas.width - this.paddleW) / 2;
    this.balls = [{
      x: this.paddleX + this.paddleW / 2,
      y: this.paddleY - 10,
      radius: 7,
      vx: 0,
      vy: 0,
      isAttached: true,
      trail: []
    }];

    // Generate Brick Matrix
    const rows = 5;
    const cols = 7;
    const padding = 6;
    const topOffset = 36;
    const brickW = (this.canvas.width - (cols + 1) * padding) / cols;
    const brickH = 20;

    const rowConfigs = [
      { color: '#ef4444', hp: 2, points: 150, name: 'RUBY' },
      { color: '#f59e0b', hp: 1, points: 100, name: 'TOPAZ' },
      { color: '#10b981', hp: 1, points: 100, name: 'EMERALD' },
      { color: '#06b6d4', hp: 1, points: 100, name: 'SAPPHIRE' },
      { color: '#8b5cf6', hp: 1, points: 80, name: 'AMETHYST' }
    ];

    this.bricks = [];
    for (let r = 0; r < rows; r++) {
      const cfg = rowConfigs[r % rowConfigs.length];
      for (let c = 0; c < cols; c++) {
        const bx = padding + c * (brickW + padding);
        const by = topOffset + r * (brickH + padding);
        this.bricks.push({
          x: bx,
          y: by,
          w: brickW,
          h: brickH,
          color: cfg.color,
          hp: cfg.hp,
          maxHp: cfg.hp,
          points: cfg.points
        });
      }
    }
  }

  _loop() {
    if (!this.isRunning || this.isPaused) return;

    try {
      this._update();
      this._draw();
    } catch (err) {
      console.error('[BouncingBall] Loop error:', err);
    }

    this.animFrameId = requestAnimationFrame(() => this._loop());
  }

  _update() {
    // 1. Update Balls
    for (let i = this.balls.length - 1; i >= 0; i--) {
      const b = this.balls[i];

      if (b.isAttached) {
        b.x = this.paddleX + this.paddleW / 2;
        b.y = this.paddleY - b.radius - 2;
        continue;
      }

      // Record motion trail
      b.trail.push({ x: b.x, y: b.y, alpha: 0.6 });
      if (b.trail.length > 5) b.trail.shift();

      b.x += b.vx;
      b.y += b.vy;

      // Left & Right Wall Collisions
      if (b.x - b.radius <= 0) {
        b.x = b.radius;
        b.vx = Math.abs(b.vx);
        if (window.gameAudio) window.gameAudio.playPaddleHit(-0.4);
      } else if (b.x + b.radius >= this.canvas.width) {
        b.x = this.canvas.width - b.radius;
        b.vx = -Math.abs(b.vx);
        if (window.gameAudio) window.gameAudio.playPaddleHit(0.4);
      }

      // Top Ceiling Collision
      if (b.y - b.radius <= 0) {
        b.y = b.radius;
        b.vy = Math.abs(b.vy);
        if (window.gameAudio) window.gameAudio.playPaddleHit(0);
      }

      // Paddle Collision
      if (
        b.y + b.radius >= this.paddleY &&
        b.y - b.radius <= this.paddleY + this.paddleH &&
        b.x >= this.paddleX - 4 &&
        b.x <= this.paddleX + this.paddleW + 4 &&
        b.vy > 0
      ) {
        // Reset combo multiplier when ball hits paddle
        this.combo = 0;

        // Dynamic angle calculation based on impact location
        const relX = (b.x - (this.paddleX + this.paddleW / 2)) / (this.paddleW / 2);
        const maxAngle = Math.PI * 0.38; // Max 68 degree bounce
        const angle = relX * maxAngle - Math.PI / 2;
        const baseSpd = this.ballBaseSpeed || 4.8;
        b.vx = Math.cos(angle) * baseSpd;
        b.vy = Math.sin(angle) * baseSpd;
        b.y = this.paddleY - b.radius;

        if (window.gameAudio) window.gameAudio.playPaddleHit(relX);
      }

      // Brick Collisions
      for (let j = this.bricks.length - 1; j >= 0; j--) {
        const brk = this.bricks[j];
        if (this._checkBallBrickCollision(b, brk)) {
          if (!this.isFireballActive) {
            // Reflect ball velocity based on collision side
            const prevX = b.x - b.vx;
            const prevY = b.y - b.vy;
            if (prevX + b.radius <= brk.x || prevX - b.radius >= brk.x + brk.w) {
              b.vx = -b.vx;
            } else {
              b.vy = -b.vy;
            }
            // Step ball position out of brick volume immediately
            b.x += b.vx;
            b.y += b.vy;
          }

          // Damage or destroy brick
          brk.hp--;
          this.combo++;
          const scoreGained = brk.points * Math.min(5, this.combo);
          if (this.framework && typeof this.framework.addScore === 'function') {
            this.framework.addScore(scoreGained);
          }

          this._spawnBrickSparks(brk.x + brk.w / 2, brk.y + brk.h / 2, brk.color);
          if (window.gameAudio && typeof window.gameAudio.playBrickBreak === 'function') {
            window.gameAudio.playBrickBreak(this.combo);
          }

          if (brk.hp <= 0) {
            if (this.framework && typeof this.framework.addItemsCollected === 'function') {
              this.framework.addItemsCollected(1);
            }
            // 22% chance to drop powerup capsule
            if (Math.random() < 0.22) {
              this._spawnPowerup(brk.x + brk.w / 2, brk.y + brk.h / 2);
            }
            this.bricks.splice(j, 1);
          }
          break;
        }
      }

      // Bottom death floor
      if (b.y - b.radius > this.canvas.height) {
        this.balls.splice(i, 1);
      }
    }

    // Check if all balls were lost
    if (this.balls.length === 0) {
      this.lives--;
      this.combo = 0;
      if (this.lives <= 0) {
        this._handleGameOver();
        return;
      } else {
        // Respawn attached ball
        this.balls.push({
          x: this.paddleX + this.paddleW / 2,
          y: this.paddleY - 10,
          radius: 7,
          vx: 0,
          vy: 0,
          isAttached: true,
          trail: []
        });
      }
    }

    // Check Level Complete (all bricks cleared)
    if (this.bricks.length === 0) {
      this.framework.setLevel(this.framework.level + 1);
      this.framework.addScore(1000);
      if (window.gameAudio) window.gameAudio.playPowerup();
      this._initLevel();
    }

    // 2. Update Falling Powerups
    for (let i = this.powerups.length - 1; i >= 0; i--) {
      const p = this.powerups[i];
      p.y += p.vy;

      // Check collision with paddle
      if (
        p.y + p.radius >= this.paddleY &&
        p.y - p.radius <= this.paddleY + this.paddleH &&
        p.x >= this.paddleX &&
        p.x <= this.paddleX + this.paddleW
      ) {
        this._activatePowerup(p.type);
        this.powerups.splice(i, 1);
        continue;
      }

      if (p.y > this.canvas.height + 20) {
        this.powerups.splice(i, 1);
      }
    }

    // 3. Update Particles
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const pt = this.particles[i];
      pt.x += pt.vx;
      pt.y += pt.vy;
      pt.alpha -= 0.03;
      if (pt.alpha <= 0) {
        this.particles.splice(i, 1);
      }
    }
  }

  _checkBallBrickCollision(ball, brick) {
    const closestX = Math.max(brick.x, Math.min(ball.x, brick.x + brick.w));
    const closestY = Math.max(brick.y, Math.min(ball.y, brick.y + brick.h));
    const dx = ball.x - closestX;
    const dy = ball.y - closestY;
    return (dx * dx + dy * dy) < (ball.radius * ball.radius);
  }

  _spawnPowerup(x, y) {
    const types = ['MULTIBALL', 'WIDE_PADDLE', 'FIREBALL', 'SLOW_MO', 'LIFE'];
    const weights = [0.35, 0.25, 0.15, 0.15, 0.10];
    const rand = Math.random();
    let sum = 0;
    let chosen = types[0];
    for (let i = 0; i < types.length; i++) {
      sum += weights[i];
      if (rand <= sum) {
        chosen = types[i];
        break;
      }
    }

    this.powerups.push({
      x,
      y,
      radius: 9,
      vy: 2.2,
      type: chosen
    });
  }

  _activatePowerup(type) {
    if (window.gameAudio) window.gameAudio.playPowerup();

    if (type === 'MULTIBALL') {
      // Split each active ball into 2 additional balls!
      const newBalls = [];
      this.balls.forEach(b => {
        if (!b.isAttached) {
          newBalls.push({
            x: b.x,
            y: b.y,
            radius: b.radius,
            vx: b.vx + (Math.random() - 0.5) * 3,
            vy: b.vy,
            isAttached: false,
            trail: []
          });
          newBalls.push({
            x: b.x,
            y: b.y,
            radius: b.radius,
            vx: b.vx - (Math.random() - 0.5) * 3,
            vy: b.vy,
            isAttached: false,
            trail: []
          });
        }
      });
      this.balls.push(...newBalls);
    } else if (type === 'WIDE_PADDLE') {
      this.paddleW = 120;
      if (this.widePaddleTimer) clearTimeout(this.widePaddleTimer);
      this.widePaddleTimer = setTimeout(() => {
        this.paddleW = 86;
      }, 14000);
    } else if (type === 'FIREBALL') {
      this.isFireballActive = true;
      if (this.fireballTimer) clearTimeout(this.fireballTimer);
      this.fireballTimer = setTimeout(() => {
        this.isFireballActive = false;
      }, 10000);
    } else if (type === 'SLOW_MO') {
      this.balls.forEach(b => {
        b.vx *= 0.75;
        b.vy *= 0.75;
      });
    } else if (type === 'LIFE') {
      this.lives = Math.min(5, this.lives + 1);
    }
  }

  _spawnBrickSparks(x, y, color) {
    for (let i = 0; i < 10; i++) {
      const angle = Math.random() * Math.PI * 2;
      const spd = Math.random() * 3 + 1.5;
      this.particles.push({
        x,
        y,
        vx: Math.cos(angle) * spd,
        vy: Math.sin(angle) * spd,
        radius: Math.random() * 2.5 + 1.5,
        color,
        alpha: 1.0
      });
    }
  }

  _handleGameOver() {
    this.isRunning = false;
    if (window.gameAudio) {
      window.gameAudio.playGameOver();
      window.gameAudio.stopMusic();
    }
    this.framework.gameOver({
      score: this.framework.score,
      itemsCollected: this.framework.itemsCollected,
      level: this.framework.level
    });
  }

  _draw() {
    const w = this.canvas.width;
    const h = this.canvas.height;

    // 1. Arcade 3D Arena Floor
    const bgGrad = this.ctx.createRadialGradient(w / 2, h / 2, 20, w / 2, h / 2, w * 0.8);
    bgGrad.addColorStop(0, '#0f172a');
    bgGrad.addColorStop(1, '#020617');
    this.ctx.fillStyle = bgGrad;
    this.ctx.fillRect(0, 0, w, h);

    // Subtle isometric arena boundary
    this.ctx.strokeStyle = 'rgba(56, 189, 248, 0.15)';
    this.ctx.lineWidth = 2;
    this.ctx.strokeRect(2, 2, w - 4, h - 4);

    // 2. Draw HUD Elements (Lives Hearts & Combo)
    this.ctx.fillStyle = '#f43f5e';
    this.ctx.font = '700 13px "Plus Jakarta Sans", sans-serif';
    this.ctx.textAlign = 'left';
    let heartsText = '';
    for (let i = 0; i < this.lives; i++) heartsText += '❤️ ';
    this.ctx.fillText(heartsText, 10, 20);

    if (this.combo > 1) {
      this.ctx.fillStyle = '#fbbf24';
      this.ctx.textAlign = 'right';
      this.ctx.fillText(`${this.combo}x COMBO!`, w - 12, 20);
    }

    // 3. Draw 3D Beveled Bricks
    this.bricks.forEach(brk => {
      this._draw3DBrick(brk);
    });

    // 4. Draw Falling Powerup Capsules
    this.powerups.forEach(p => {
      this._drawPowerupCapsule(p);
    });

    // 5. Draw 3D Chrome Shiny Ball(s)
    this.balls.forEach(b => {
      this._draw3DBall(b);
    });

    // 6. Draw 3D Glowing Futuristic Paddle
    this._draw3DPaddle();

    // 7. Draw Particles
    this.particles.forEach(pt => {
      this.ctx.fillStyle = pt.color;
      this.ctx.globalAlpha = pt.alpha;
      this.ctx.beginPath();
      this.ctx.arc(pt.x, pt.y, pt.radius, 0, Math.PI * 2);
      this.ctx.fill();
    });
    this.ctx.globalAlpha = 1.0;
  }

  _draw3DBrick(brk) {
    const x = brk.x;
    const y = brk.y;
    const bw = brk.w;
    const bh = brk.h;

    // Floor drop shadow
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
    this.ctx.fillRect(x + 2, y + 2, bw, bh);

    // Base volumetric block fill
    this.ctx.fillStyle = brk.color;
    this.ctx.beginPath();
    this.ctx.roundRect(x, y, bw, bh, 3);
    this.ctx.fill();

    // 3D Top Specular Bevel
    this.ctx.fillStyle = 'rgba(255, 255, 255, 0.45)';
    this.ctx.beginPath();
    this.ctx.moveTo(x, y);
    this.ctx.lineTo(x + bw, y);
    this.ctx.lineTo(x + bw - 3, y + 3);
    this.ctx.lineTo(x + 3, y + 3);
    this.ctx.closePath();
    this.ctx.fill();

    // 3D Left Specular Bevel
    this.ctx.fillStyle = 'rgba(255, 255, 255, 0.25)';
    this.ctx.beginPath();
    this.ctx.moveTo(x, y);
    this.ctx.lineTo(x + 3, y + 3);
    this.ctx.lineTo(x + 3, y + bh - 3);
    this.ctx.lineTo(x, y + bh);
    this.ctx.closePath();
    this.ctx.fill();

    // 3D Bottom & Right Dark Bevel
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.40)';
    this.ctx.beginPath();
    this.ctx.moveTo(x + bw, y);
    this.ctx.lineTo(x + bw, y + bh);
    this.ctx.lineTo(x, y + bh);
    this.ctx.lineTo(x + 3, y + bh - 3);
    this.ctx.lineTo(x + bw - 3, y + bh - 3);
    this.ctx.lineTo(x + bw - 3, y + 3);
    this.ctx.closePath();
    this.ctx.fill();

    // Cracks indicator if multi-hp damaged
    if (brk.hp < brk.maxHp) {
      this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
      this.ctx.lineWidth = 1.5;
      this.ctx.beginPath();
      this.ctx.moveTo(x + bw * 0.3, y + 2);
      this.ctx.lineTo(x + bw * 0.45, y + bh * 0.6);
      this.ctx.lineTo(x + bw * 0.7, y + bh - 2);
      this.ctx.stroke();
    }
  }

  _draw3DBall(b) {
    // Draw motion trail
    b.trail.forEach(t => {
      this.ctx.fillStyle = this.isFireballActive ? 'rgba(239, 68, 68, 0.35)' : 'rgba(56, 189, 248, 0.25)';
      this.ctx.beginPath();
      this.ctx.arc(t.x, t.y, b.radius * 0.8, 0, Math.PI * 2);
      this.ctx.fill();
    });

    const x = b.x;
    const y = b.y;
    const r = b.radius;

    // 3D Spherical Radial Gradient
    const ballGrad = this.ctx.createRadialGradient(
      x - r * 0.35,
      y - r * 0.35,
      r * 0.08,
      x,
      y,
      r
    );

    if (this.isFireballActive) {
      ballGrad.addColorStop(0, '#ffffff');
      ballGrad.addColorStop(0.3, '#fde047');
      ballGrad.addColorStop(0.7, '#ef4444');
      ballGrad.addColorStop(1, '#991b1b');
    } else {
      ballGrad.addColorStop(0, '#ffffff');
      ballGrad.addColorStop(0.3, '#e0f2fe');
      ballGrad.addColorStop(0.7, '#38bdf8');
      ballGrad.addColorStop(1, '#0369a1');
    }

    this.ctx.fillStyle = ballGrad;
    this.ctx.beginPath();
    this.ctx.arc(x, y, r, 0, Math.PI * 2);
    this.ctx.fill();

    // Bright Specular Catchlight
    this.ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
    this.ctx.beginPath();
    this.ctx.arc(x - r * 0.35, y - r * 0.35, r * 0.28, 0, Math.PI * 2);
    this.ctx.fill();
  }

  _draw3DPaddle() {
    const x = this.paddleX;
    const y = this.paddleY;
    const w = this.paddleW;
    const h = this.paddleH;

    // Floor drop shadow
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
    this.ctx.beginPath();
    this.ctx.roundRect(x + 2, y + 4, w, h, 6);
    this.ctx.fill();

    // 3D Metallic Paddle Body
    const padGrad = this.ctx.createLinearGradient(x, y, x, y + h);
    padGrad.addColorStop(0, '#94a3b8');
    padGrad.addColorStop(0.3, '#f1f5f9');
    padGrad.addColorStop(0.7, '#475569');
    padGrad.addColorStop(1, '#1e293b');
    this.ctx.fillStyle = padGrad;
    this.ctx.beginPath();
    this.ctx.roundRect(x, y, w, h, 6);
    this.ctx.fill();

    // Glowing Cyan Trim Rim
    this.ctx.strokeStyle = '#38bdf8';
    this.ctx.lineWidth = 1.8;
    this.ctx.stroke();

    // Center power indicator light
    this.ctx.fillStyle = this.isFireballActive ? '#ef4444' : '#10b981';
    this.ctx.beginPath();
    this.ctx.arc(x + w / 2, y + h / 2, 3, 0, Math.PI * 2);
    this.ctx.fill();
  }

  _drawPowerupCapsule(p) {
    const x = p.x;
    const y = p.y;
    const r = p.radius;

    const colors = {
      MULTIBALL: '#38bdf8',
      WIDE_PADDLE: '#10b981',
      FIREBALL: '#ef4444',
      SLOW_MO: '#8b5cf6',
      LIFE: '#f43f5e'
    };
    const col = colors[p.type] || '#f59e0b';

    this.ctx.fillStyle = col;
    this.ctx.shadowColor = col;
    this.ctx.shadowBlur = 6;
    this.ctx.beginPath();
    this.ctx.roundRect(x - r, y - r, r * 2, r * 2, 4);
    this.ctx.fill();
    this.ctx.shadowBlur = 0;

    // Capsule Letter
    this.ctx.fillStyle = '#ffffff';
    this.ctx.font = '900 10px monospace';
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'middle';
    const letter = p.type[0];
    this.ctx.fillText(letter, x, y);
  }

  _drawIdle() {
    const w = this.canvas.width;
    const h = this.canvas.height;
    this.ctx.fillStyle = '#0f172a';
    this.ctx.fillRect(0, 0, w, h);

    this.ctx.fillStyle = '#94a3b8';
    this.ctx.font = '600 13px "Plus Jakarta Sans", sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.fillText('Press "Start Game" or Tap to Launch Ball', w / 2, h / 2);
  }
}
