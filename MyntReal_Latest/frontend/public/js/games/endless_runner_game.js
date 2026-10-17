/**
 * Game C: Configurable Endless Runner Engine (DC Protocol Oct 2026)
 * Continuous side-scrolling runner with pluggable character configuration,
 * gravity, double-jump physics, ground obstacles, aerial hazards, and collectibles.
 */

class EndlessRunnerGame {
  constructor(canvas, framework) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.framework = framework;

    this.characterId = 'volt_fox';
    this.character = window.RUNNER_CHARACTERS[this.characterId] || window.RUNNER_CHARACTERS['volt_fox'];

    this.isRunning = false;
    this.isPaused = false;
    this.animFrameId = null;

    // Physics parameters
    this.gravity = 0.55;
    this.groundY = 0; // Calculated on resize
    this.playerX = 60;
    this.playerY = 0;
    this.vy = 0;
    this.isGrounded = false;
    this.jumpCount = 0;
    this.maxJumps = 2; // Double jump support!

    this.baseSpeed = 5.0;
    this.speed = 5.0;
    this.distance = 0;
    this.coins = 0;
    this.animFrame = 0;

    // Obstacles & Collectibles
    this.obstacles = [];
    this.collectibles = [];
    this.nextObstacleDistance = 250;
    this.nextCoinDistance = 120;

    // Parallax background layers
    this.stars = [];
    this.cityBuildings = [];

    this._bindControls();
    this.resizeCanvas();
    window.addEventListener('resize', () => this.resizeCanvas());
  }

  setCharacter(charId) {
    if (window.RUNNER_CHARACTERS && window.RUNNER_CHARACTERS[charId]) {
      this.characterId = charId;
      this.character = window.RUNNER_CHARACTERS[charId];
    }
  }

  resizeCanvas() {
    if (!this.canvas || !this.canvas.parentElement) return;
    const parentWidth = this.canvas.parentElement.clientWidth;
    const w = Math.min(parentWidth - 24, 680);
    const h = Math.min(window.innerHeight * 0.48, 380);

    this.canvas.width = w;
    this.canvas.height = h;
    this.groundY = h - 60;
    this.playerY = this.groundY - this.character.height;

    this._initParallax();
    if (!this.isRunning) this._drawIdle();
  }

  _initParallax() {
    const w = this.canvas.width;
    const h = this.canvas.height;

    // Generate static stars
    this.stars = Array.from({ length: 30 }, () => ({
      x: Math.random() * w,
      y: Math.random() * (this.groundY - 80),
      size: Math.random() * 2 + 1,
      alpha: Math.random() * 0.7 + 0.3
    }));

    // Generate skyline buildings
    let curX = 0;
    this.cityBuildings = [];
    while (curX < w * 2) {
      const bw = Math.random() * 50 + 35;
      const bh = Math.random() * 90 + 50;
      this.cityBuildings.push({
        x: curX,
        w: bw,
        h: bh,
        color: `rgba(30, 41, 59, ${Math.random() * 0.4 + 0.4})`
      });
      curX += bw + 8;
    }
  }

  _bindControls() {
    window.addEventListener('keydown', (e) => {
      if (!this.isRunning || this.isPaused) return;
      if (['ArrowUp', 'Space', 'KeyW'].includes(e.code)) {
        this.jump();
      }
    });

    // Touch / click anywhere on canvas jumps
    this.canvas.addEventListener('touchstart', (e) => {
      if (!this.isRunning || this.isPaused) return;
      this.jump();
    }, { passive: true });

    this.canvas.addEventListener('mousedown', (e) => {
      if (!this.isRunning || this.isPaused) return;
      this.jump();
    });
  }

  jump() {
    if (this.jumpCount < this.maxJumps) {
      this.vy = -11.5;
      this.isGrounded = false;
      this.jumpCount++;
      if (window.gameAudio) window.gameAudio.playJump();
    }
  }

  start() {
    this.reset();
    this.isRunning = true;
    this.isPaused = false;
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

    this.playerY = this.groundY - this.character.height;
    this.vy = 0;
    this.isGrounded = true;
    this.jumpCount = 0;

    this.speed = this.baseSpeed;
    this.distance = 0;
    this.coins = 0;
    this.animFrame = 0;

    this.obstacles = [];
    this.collectibles = [];
    this.nextObstacleDistance = 200;
    this.nextCoinDistance = 100;
  }

  _loop() {
    if (!this.isRunning || this.isPaused) return;

    this._update();
    this._draw();

    this.animFrameId = requestAnimationFrame(() => this._loop());
  }

  _update() {
    this.animFrame++;

    // Accelerate runner speed gradually
    this.speed = Math.min(10.5, this.baseSpeed + (this.distance * 0.0015));

    // Update distance
    this.distance += Math.floor(this.speed * 0.25);
    this.framework.setDistance(this.distance);
    this.framework.addScore(1);

    // Milestones every 250m
    const lvl = Math.floor(this.distance / 250) + 1;
    this.framework.setLevel(lvl);
    if (this.distance > 0 && this.distance % 250 < 3) {
      this.framework.recordMilestone(this.distance);
    }

    // Apply Player Gravity
    this.vy += this.gravity;
    this.playerY += this.vy;

    if (this.playerY >= this.groundY - this.character.height) {
      this.playerY = this.groundY - this.character.height;
      this.vy = 0;
      this.isGrounded = true;
      this.jumpCount = 0;
    } else {
      this.isGrounded = false;
    }

    // Spawn Obstacles
    this.nextObstacleDistance -= this.speed;
    if (this.nextObstacleDistance <= 0) {
      this._spawnObstacle();
      this.nextObstacleDistance = Math.random() * 260 + 200;
    }

    // Spawn Collectibles (Stars)
    this.nextCoinDistance -= this.speed;
    if (this.nextCoinDistance <= 0) {
      this._spawnCollectible();
      this.nextCoinDistance = Math.random() * 180 + 120;
    }

    // Update Obstacles position & collision
    const charBounds = {
      x: this.playerX + 4,
      y: this.playerY + 4,
      w: this.character.width - 8,
      h: this.character.height - 6
    };

    for (let i = this.obstacles.length - 1; i >= 0; i--) {
      const obs = this.obstacles[i];
      obs.x -= this.speed;

      // AABB Collision check
      if (
        charBounds.x < obs.x + obs.w &&
        charBounds.x + charBounds.w > obs.x &&
        charBounds.y < obs.y + obs.h &&
        charBounds.y + charBounds.h > obs.y
      ) {
        this._handleCollision();
        return;
      }

      if (obs.x + obs.w < -20) {
        this.obstacles.splice(i, 1);
      }
    }

    // Update Collectibles position & collection
    for (let i = this.collectibles.length - 1; i >= 0; i--) {
      const c = this.collectibles[i];
      c.x -= this.speed;

      // Circle to box collision
      const closeX = Math.max(charBounds.x, Math.min(c.x, charBounds.x + charBounds.w));
      const closeY = Math.max(charBounds.y, Math.min(c.y, charBounds.y + charBounds.h));
      const dist = Math.hypot(c.x - closeX, c.y - closeY);

      if (dist < c.radius) {
        if (window.gameAudio) window.gameAudio.playCollect();
        this.coins++;
        this.framework.addScore(25);
        this.framework.setItems(this.coins);
        this.collectibles.splice(i, 1);
        continue;
      }

      if (c.x < -20) {
        this.collectibles.splice(i, 1);
      }
    }

    // Parallax update
    this.cityBuildings.forEach(b => {
      b.x -= this.speed * 0.3;
      if (b.x + b.w < 0) {
        b.x = this.canvas.width + Math.random() * 30;
      }
    });
  }

  _spawnObstacle() {
    const isAerial = Math.random() > 0.65;
    if (isAerial) {
      // Hovering aerial drone
      this.obstacles.push({
        type: 'DRONE',
        x: this.canvas.width + 20,
        y: this.groundY - 75,
        w: 32,
        h: 22,
        color: '#f43f5e'
      });
    } else {
      // Ground energy barrier / spikes
      const obsHeight = Math.random() > 0.5 ? 36 : 26;
      this.obstacles.push({
        type: 'GROUND',
        x: this.canvas.width + 20,
        y: this.groundY - obsHeight,
        w: 24,
        h: obsHeight,
        color: '#ef4444'
      });
    }
  }

  _spawnCollectible() {
    this.collectibles.push({
      x: this.canvas.width + 20,
      y: this.groundY - (Math.random() * 80 + 35),
      radius: 8,
      color: '#fbbf24'
    });
  }

  _handleCollision() {
    this.isRunning = false;
    if (window.gameAudio) window.gameAudio.playCollision();
    this.framework.gameOver({
      score: this.framework.score,
      distanceTravelled: this.distance,
      itemsCollected: this.coins,
      level: this.framework.level
    });
  }

  _draw() {
    const w = this.canvas.width;
    const h = this.canvas.height;

    // Sky Background Gradient
    const skyGrad = this.ctx.createLinearGradient(0, 0, 0, this.groundY);
    skyGrad.addColorStop(0, '#090e17');
    skyGrad.addColorStop(1, '#0f172a');
    this.ctx.fillStyle = skyGrad;
    this.ctx.fillRect(0, 0, w, h);

    // Stars
    this.ctx.fillStyle = '#94a3b8';
    this.stars.forEach(s => {
      this.ctx.globalAlpha = s.alpha;
      this.ctx.fillRect(s.x, s.y, s.size, s.size);
    });
    this.ctx.globalAlpha = 1.0;

    // Distant City Skyline
    this.cityBuildings.forEach(b => {
      this.ctx.fillStyle = b.color;
      this.ctx.fillRect(b.x, this.groundY - b.h, b.w, b.h);
      // Building windows
      this.ctx.fillStyle = 'rgba(254, 240, 138, 0.25)';
      for (let wy = this.groundY - b.h + 8; wy < this.groundY - 8; wy += 14) {
        this.ctx.fillRect(b.x + 6, wy, 4, 6);
        if (b.w > 30) this.ctx.fillRect(b.x + 18, wy, 4, 6);
      }
    });

    // Running Ground Platform
    this.ctx.fillStyle = '#1e293b';
    this.ctx.fillRect(0, this.groundY, w, h - this.groundY);

    // Neon Track Border
    this.ctx.strokeStyle = '#38bdf8';
    this.ctx.lineWidth = 3;
    this.ctx.beginPath();
    this.ctx.moveTo(0, this.groundY);
    this.ctx.lineTo(w, this.groundY);
    this.ctx.stroke();

    // Moving ground dash stripes
    this.ctx.strokeStyle = 'rgba(56, 189, 248, 0.4)';
    this.ctx.lineWidth = 2;
    const offset = (this.animFrame * this.speed) % 30;
    for (let x = -offset; x < w; x += 30) {
      this.ctx.beginPath();
      this.ctx.moveTo(x, this.groundY + 12);
      this.ctx.lineTo(x + 14, this.groundY + 12);
      this.ctx.stroke();
    }

    // Draw Obstacles
    this.obstacles.forEach(obs => {
      if (obs.type === 'DRONE') {
        // Floating Drone
        this.ctx.fillStyle = obs.color;
        this.ctx.beginPath();
        this.ctx.roundRect(obs.x, obs.y, obs.w, obs.h, 6);
        this.ctx.fill();
        // Rotor blades
        const rotorAngle = Math.sin(this.animFrame * 0.8) * 8;
        this.ctx.strokeStyle = '#fda4af';
        this.ctx.lineWidth = 2;
        this.ctx.beginPath();
        this.ctx.moveTo(obs.x - 4, obs.y + rotorAngle);
        this.ctx.lineTo(obs.x + obs.w + 4, obs.y - rotorAngle);
        this.ctx.stroke();
        // Visor
        this.ctx.fillStyle = '#ffe4e6';
        this.ctx.fillRect(obs.x + 6, obs.y + 6, 8, 4);
      } else {
        // Ground Barrier
        this.ctx.fillStyle = obs.color;
        this.ctx.beginPath();
        this.ctx.moveTo(obs.x, obs.y + obs.h);
        this.ctx.lineTo(obs.x + obs.w / 2, obs.y);
        this.ctx.lineTo(obs.x + obs.w, obs.y + obs.h);
        this.ctx.closePath();
        this.ctx.fill();

        // Pulsing warning tip
        this.ctx.fillStyle = '#fef08a';
        this.ctx.beginPath();
        this.ctx.arc(obs.x + obs.w / 2, obs.y + 4, 3, 0, Math.PI * 2);
        this.ctx.fill();
      }
    });

    // Draw Collectible Stars
    this.collectibles.forEach(c => {
      const pulse = Math.sin(this.animFrame * 0.15) * 2;
      this.ctx.fillStyle = c.color;
      this.ctx.shadowColor = 'rgba(251, 191, 36, 0.8)';
      this.ctx.shadowBlur = 8;
      this.ctx.beginPath();
      this.ctx.arc(c.x, c.y, c.radius + pulse, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.shadowBlur = 0;

      // Inner sparkle
      this.ctx.fillStyle = '#fffbeb';
      this.ctx.beginPath();
      this.ctx.arc(c.x, c.y, (c.radius + pulse) * 0.4, 0, Math.PI * 2);
      this.ctx.fill();
    });

    // Draw Configurable Player Character
    const playerState = this.isGrounded ? 'RUNNING' : 'JUMPING';
    if (this.character && typeof this.character.draw === 'function') {
      this.character.draw(this.ctx, this.playerX, this.playerY, this.animFrame, playerState);
    }
  }

  _drawIdle() {
    const w = this.canvas.width;
    const h = this.canvas.height;
    this.ctx.fillStyle = '#090e17';
    this.ctx.fillRect(0, 0, w, h);

    this.ctx.fillStyle = '#94a3b8';
    this.ctx.font = '600 13px "Plus Jakarta Sans", sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.fillText('Press "Start Game" or Tap to Jump', w / 2, h / 2);
  }
}
