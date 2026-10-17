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
    this.tickInterval = 110;
    this.lastTickTime = 0;
    this.animFrameId = null;

    this._bindControls();
    this.resizeCanvas();
    window.addEventListener('resize', () => this.resizeCanvas());
  }

  resizeCanvas() {
    if (!this.canvas || !this.canvas.parentElement) return;
    const parentWidth = this.canvas.parentElement.clientWidth;
    const size = Math.min(parentWidth - 24, 440);
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
        if (dx > 30 && this.direction.x === 0) this.nextDirection = { x: 1, y: 0 };
        else if (dx < -30 && this.direction.x === 0) this.nextDirection = { x: -1, y: 0 };
      } else {
        if (dy > 30 && this.direction.y === 0) this.nextDirection = { x: 0, y: 1 };
        else if (dy < -30 && this.direction.y === 0) this.nextDirection = { x: 0, y: -1 };
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
    this.tickInterval = 110;
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
    const head = {
      x: this.snake[0].x + this.direction.x,
      y: this.snake[0].y + this.direction.y
    };

    // Wall collision detection
    if (head.x < 0 || head.x >= this.gridSize || head.y < 0 || head.y >= this.gridSize) {
      this._handleCollision();
      return;
    }

    // Self collision detection
    for (let i = 0; i < this.snake.length; i++) {
      if (this.snake[i].x === head.x && this.snake[i].y === head.y) {
        this._handleCollision();
        return;
      }
    }

    this.snake.unshift(head);

    // Food eaten check
    if (head.x === this.food.x && head.y === this.food.y) {
      this._createParticleBurst(head.x * this.tileSize, head.y * this.tileSize, '#f59e0b');
      if (window.gameAudio) window.gameAudio.playCollect();

      this.framework.addScore(10);
      const foodCount = (this.snake.length - 3);
      this.framework.setItems(foodCount);

      // Progressive speed acceleration down to 60ms
      this.tickInterval = Math.max(60, 110 - (foodCount * 1.5));
      const lvl = Math.floor(foodCount / 5) + 1;
      this.framework.setLevel(lvl);

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
    if (window.gameAudio) window.gameAudio.playCollision();
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

  _draw() {
    const w = this.canvas.width;
    const h = this.canvas.height;
    const ts = this.tileSize;

    // Background Grid
    this.ctx.fillStyle = '#090e17';
    this.ctx.fillRect(0, 0, w, h);

    // Subtle grid lines
    this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
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

    // Draw Food with pulsing glow
    const fx = this.food.x * ts;
    const fy = this.food.y * ts;
    const pulse = Math.sin(performance.now() * 0.008) * 2;

    this.ctx.fillStyle = '#f59e0b';
    this.ctx.shadowColor = 'rgba(245, 158, 11, 0.8)';
    this.ctx.shadowBlur = 10;
    this.ctx.beginPath();
    this.ctx.arc(fx + ts / 2, fy + ts / 2, (ts / 2 - 2) + pulse, 0, Math.PI * 2);
    this.ctx.fill();
    this.ctx.shadowBlur = 0;

    // Draw Snake
    this.snake.forEach((seg, index) => {
      const sx = seg.x * ts;
      const sy = seg.y * ts;

      if (index === 0) {
        // Head
        this.ctx.fillStyle = '#10b981';
        this.ctx.shadowColor = 'rgba(16, 185, 129, 0.6)';
        this.ctx.shadowBlur = 8;
        this.ctx.beginPath();
        this.ctx.roundRect(sx + 1, sy + 1, ts - 2, ts - 2, 6);
        this.ctx.fill();
        this.ctx.shadowBlur = 0;

        // Eyes
        this.ctx.fillStyle = '#022c22';
        const eyeOffset = ts / 4;
        this.ctx.beginPath();
        this.ctx.arc(sx + eyeOffset, sy + eyeOffset, 2, 0, Math.PI * 2);
        this.ctx.arc(sx + ts - eyeOffset, sy + eyeOffset, 2, 0, Math.PI * 2);
        this.ctx.fill();
      } else {
        // Body with gradient fade
        const progress = 1 - (index / this.snake.length) * 0.4;
        this.ctx.fillStyle = `rgba(16, 185, 129, ${progress})`;
        this.ctx.beginPath();
        this.ctx.roundRect(sx + 2, sy + 2, ts - 4, ts - 4, 4);
        this.ctx.fill();
      }
    });

    // Draw particle bursts
    this.particles.forEach(p => {
      this.ctx.fillStyle = p.color;
      this.ctx.globalAlpha = p.alpha;
      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
      this.ctx.fill();
    });
    this.ctx.globalAlpha = 1.0;
  }

  _drawIdle() {
    const w = this.canvas.width;
    const h = this.canvas.height;
    this.ctx.fillStyle = '#090e17';
    this.ctx.fillRect(0, 0, w, h);

    this.ctx.fillStyle = '#94a3b8';
    this.ctx.font = '600 14px "Plus Jakarta Sans", sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.fillText('Press "Start Game" to begin', w / 2, h / 2);
  }
}
