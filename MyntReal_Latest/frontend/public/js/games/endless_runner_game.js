/**
 * Game C: Configurable Endless Runner Engine (DC Protocol Oct 2026)
 * Continuous side-scrolling runner with pluggable character configuration,
 * gravity, double-jump physics, ground obstacles, aerial hazards, and collectibles.
 * Upgraded with relaxed casual speeds and rich 3D colorful aesthetics.
 */

class EndlessRunnerGame {
  constructor(canvas, framework) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.framework = framework;

    this.characterId = 'volt_fox';
    this.character = (window.RUNNER_CHARACTERS && window.RUNNER_CHARACTERS[this.characterId]) ||
      (window.RUNNER_CHARACTERS && window.RUNNER_CHARACTERS['volt_fox']) || {
        name: 'Volt Fox', width: 36, height: 36,
        draw: (ctx, x, y) => { ctx.fillStyle = '#f59e0b'; ctx.fillRect(x, y, 36, 36); }
      };

    this.isRunning = false;
    this.isPaused = false;
    this.animFrameId = null;

    // Physics parameters - relaxed, floaty and controllable
    this.gravity = 0.40;
    this.groundY = 0; // Calculated on resize
    this.playerX = 60;
    this.playerY = 0;
    this.vy = 0;
    this.isGrounded = false;
    this.jumpCount = 0;
    this.maxJumps = 2; // Double jump support

    // Relaxed chill speeds & Speed modes
    this.speedMode = 'NORMAL';
    this.baseSpeed = 2.6;
    this.maxSpeed = 5.0;
    this.speed = 2.6;
    this.distance = 0;
    this.coins = 0;
    this.animFrame = 0;

    // Obstacles & Collectibles
    this.obstacles = [];
    this.collectibles = [];
    this.nextObstacleDistance = 320;
    this.nextCoinDistance = 140;

    // Parallax background layers
    this.stars = [];
    this.cityBuildings = [];

    this._bindControls();
    this.resizeCanvas();
    window.addEventListener('resize', () => this.resizeCanvas());
  }

  setSpeedMode(mode) {
    this.speedMode = mode;
    if (mode === 'SLOW') {
      this.baseSpeed = 1.8;
      this.maxSpeed = 3.6;
    } else if (mode === 'FAST') {
      this.baseSpeed = 3.6;
      this.maxSpeed = 6.4;
    } else if (mode === 'TURBO') {
      this.baseSpeed = 4.8;
      this.maxSpeed = 8.0;
    } else { // NORMAL
      this.baseSpeed = 2.6;
      this.maxSpeed = 5.0;
    }
    this.speed = this.baseSpeed;
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
    const w = Math.min(parentWidth - 16, 680);
    const h = Math.min(window.innerHeight * 0.36, 320);

    this.canvas.width = w;
    this.canvas.height = h;
    this.groundY = h - 55;
    this.playerY = this.groundY - this.character.height;

    this._initParallax();
    if (!this.isRunning) this._drawIdle();
  }

  _initParallax() {
    const w = this.canvas.width;
    const h = this.canvas.height;

    // Generate static stars
    this.stars = Array.from({ length: 32 }, () => ({
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

      if (e.code === 'Space' || e.code === 'ArrowUp' || e.code === 'KeyW') {
        e.preventDefault();
        this.jump();
      }
    });

    this.canvas.addEventListener('pointerdown', (e) => {
      if (!this.isRunning || this.isPaused) return;
      this.jump();
    });

    this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());
  }

  jump() {
    if (this.jumpCount < this.maxJumps) {
      this.vy = -9.0;
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
    this.nextObstacleDistance = 320;
    this.nextCoinDistance = 140;
  }

  _loop() {
    if (!this.isRunning || this.isPaused) return;

    this._update();
    this._draw();

    this.animFrameId = requestAnimationFrame(() => this._loop());
  }

  _update() {
    this.animFrame++;

    // Accelerate runner speed gradually and gently based on speed mode
    const maxSpd = this.maxSpeed || 5.0;
    this.speed = Math.min(maxSpd, this.baseSpeed + (this.distance * 0.0005));

    // Update distance
    this.distance += Math.floor(this.speed * 0.22);
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

    // Spawn Obstacles with generous spacing for casual play
    this.nextObstacleDistance -= this.speed;
    if (this.nextObstacleDistance <= 0) {
      this._spawnObstacle();
      this.nextObstacleDistance = Math.random() * 280 + 260;
    }

    // Spawn Collectibles (Stars)
    this.nextCoinDistance -= this.speed;
    if (this.nextCoinDistance <= 0) {
      this._spawnCollectible();
      this.nextCoinDistance = Math.random() * 200 + 140;
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

      const dx = (this.playerX + this.character.width / 2) - c.x;
      const dy = (this.playerY + this.character.height / 2) - c.y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (dist < c.radius + this.character.width / 2) {
        // Collect star!
        this.coins++;
        this.framework.addItemsCollected(1);
        this.framework.addScore(150);
        if (window.gameAudio) window.gameAudio.playCollect();
        this.collectibles.splice(i, 1);
        continue;
      }

      if (c.x < -20) {
        this.collectibles.splice(i, 1);
      }
    }

    // Move parallax city buildings
    this.cityBuildings.forEach(b => {
      b.x -= this.speed * 0.25;
      if (b.x + b.w < 0) {
        b.x = this.canvas.width + Math.random() * 20;
      }
    });

    // Move stars
    this.stars.forEach(s => {
      s.x -= this.speed * 0.08;
      if (s.x < 0) s.x = this.canvas.width;
    });
  }

  _spawnObstacle() {
    const isAerial = Math.random() > 0.65;
    if (isAerial) {
      // Hovering aerial 3D drone
      this.obstacles.push({
        type: 'DRONE',
        x: this.canvas.width + 20,
        y: this.groundY - 78,
        w: 32,
        h: 22,
        color: '#f43f5e'
      });
    } else {
      // Ground energy barrier / 3D beveled crystal spikes
      const obsHeight = Math.random() > 0.5 ? 34 : 24;
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
      radius: 9,
      color: '#fbbf24'
    });
  }

  _handleCollision() {
    this.isRunning = false;
    if (window.gameAudio) {
      if (typeof window.gameAudio.stopMusic === 'function') window.gameAudio.stopMusic();
      window.gameAudio.playCollision();
    }
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

    // Sky Background 3D Depth Gradient
    const skyGrad = this.ctx.createLinearGradient(0, 0, 0, this.groundY);
    skyGrad.addColorStop(0, '#060a12');
    skyGrad.addColorStop(0.65, '#0f172a');
    skyGrad.addColorStop(1, '#1e1b4b');
    this.ctx.fillStyle = skyGrad;
    this.ctx.fillRect(0, 0, w, h);

    // Stars with twinkling
    this.stars.forEach(s => {
      this.ctx.fillStyle = '#94a3b8';
      this.ctx.globalAlpha = s.alpha * (0.8 + Math.sin(this.animFrame * 0.05 + s.x) * 0.2);
      this.ctx.beginPath();
      this.ctx.arc(s.x, s.y, s.size * 0.8, 0, Math.PI * 2);
      this.ctx.fill();
    });
    this.ctx.globalAlpha = 1.0;

    // Distant City Skyline with illuminated 3D depth
    this.cityBuildings.forEach(b => {
      this.ctx.fillStyle = b.color;
      this.ctx.fillRect(b.x, this.groundY - b.h, b.w, b.h);

      // Building windows
      this.ctx.fillStyle = 'rgba(254, 240, 138, 0.35)';
      for (let wy = this.groundY - b.h + 8; wy < this.groundY - 8; wy += 14) {
        this.ctx.fillRect(b.x + 6, wy, 4, 6);
        if (b.w > 30) this.ctx.fillRect(b.x + 18, wy, 4, 6);
      }
    });

    // Running Ground 3D Beveled Platform
    const groundGrad = this.ctx.createLinearGradient(0, this.groundY, 0, h);
    groundGrad.addColorStop(0, '#1e293b');
    groundGrad.addColorStop(0.3, '#0f172a');
    groundGrad.addColorStop(1, '#020617');
    this.ctx.fillStyle = groundGrad;
    this.ctx.fillRect(0, this.groundY, w, h - this.groundY);

    // Glowing 3D Neon Track Rim
    this.ctx.strokeStyle = '#38bdf8';
    this.ctx.lineWidth = 3;
    this.ctx.beginPath();
    this.ctx.moveTo(0, this.groundY);
    this.ctx.lineTo(w, this.groundY);
    this.ctx.stroke();

    // Secondary neon glow line
    this.ctx.strokeStyle = 'rgba(56, 189, 248, 0.3)';
    this.ctx.lineWidth = 6;
    this.ctx.beginPath();
    this.ctx.moveTo(0, this.groundY + 2);
    this.ctx.lineTo(w, this.groundY + 2);
    this.ctx.stroke();

    // Moving ground dash stripes (isometric perspective)
    this.ctx.strokeStyle = 'rgba(56, 189, 248, 0.5)';
    this.ctx.lineWidth = 2;
    const offset = (this.animFrame * this.speed) % 32;
    for (let x = -offset; x < w; x += 32) {
      this.ctx.beginPath();
      this.ctx.moveTo(x, this.groundY + 14);
      this.ctx.lineTo(x + 16, this.groundY + 14);
      this.ctx.stroke();
    }

    // Draw Obstacles (3D Spikes and Drones)
    this.obstacles.forEach(obs => {
      if (obs.type === 'DRONE') {
        // 3D Metallic Hovering Drone
        const droneGrad = this.ctx.createLinearGradient(obs.x, obs.y, obs.x, obs.y + obs.h);
        droneGrad.addColorStop(0, '#fda4af');
        droneGrad.addColorStop(0.5, '#e11d48');
        droneGrad.addColorStop(1, '#881337');
        this.ctx.fillStyle = droneGrad;
        this.ctx.beginPath();
        this.ctx.roundRect(obs.x, obs.y, obs.w, obs.h, 6);
        this.ctx.fill();

        // 3D Specular Highlight on Drone
        this.ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
        this.ctx.fillRect(obs.x + 3, obs.y + 2, obs.w - 6, 2);

        // Spinning Rotor Blades
        const rotorAngle = Math.sin(this.animFrame * 0.8) * 8;
        this.ctx.strokeStyle = '#38bdf8';
        this.ctx.lineWidth = 2;
        this.ctx.beginPath();
        this.ctx.moveTo(obs.x - 4, obs.y + rotorAngle);
        this.ctx.lineTo(obs.x + obs.w + 4, obs.y - rotorAngle);
        this.ctx.stroke();

        // Cyber Visor Eye
        this.ctx.fillStyle = '#67e8f9';
        this.ctx.shadowColor = '#06b6d4';
        this.ctx.shadowBlur = 6;
        this.ctx.fillRect(obs.x + 8, obs.y + 7, 10, 5);
        this.ctx.shadowBlur = 0;
      } else {
        // 3D Volumetric Ground Crystal Spikes
        const spikeGrad = this.ctx.createLinearGradient(obs.x, obs.y, obs.x + obs.w, obs.y + obs.h);
        spikeGrad.addColorStop(0, '#f87171');
        spikeGrad.addColorStop(0.5, '#dc2626');
        spikeGrad.addColorStop(1, '#7f1d1d');
        this.ctx.fillStyle = spikeGrad;
        this.ctx.beginPath();
        this.ctx.moveTo(obs.x, obs.y + obs.h);
        this.ctx.lineTo(obs.x + obs.w / 2, obs.y);
        this.ctx.lineTo(obs.x + obs.w, obs.y + obs.h);
        this.ctx.closePath();
        this.ctx.fill();

        // 3D Left Bevel Highlight
        this.ctx.fillStyle = 'rgba(255, 255, 255, 0.45)';
        this.ctx.beginPath();
        this.ctx.moveTo(obs.x, obs.y + obs.h);
        this.ctx.lineTo(obs.x + obs.w / 2, obs.y);
        this.ctx.lineTo(obs.x + obs.w / 2, obs.y + obs.h);
        this.ctx.closePath();
        this.ctx.fill();

        // Glowing pulsing core
        this.ctx.fillStyle = '#fef08a';
        this.ctx.beginPath();
        this.ctx.arc(obs.x + obs.w / 2, obs.y + 5, 3.5, 0, Math.PI * 2);
        this.ctx.fill();
      }
    });

    // Draw Collectible 3D Gold Coins
    this.collectibles.forEach(c => {
      const bob = Math.sin(this.animFrame * 0.1) * 3;
      const cy = c.y + bob;

      // 3D Spherical Gold Coin
      const coinGrad = this.ctx.createRadialGradient(
        c.x - c.radius * 0.3,
        cy - c.radius * 0.3,
        1,
        c.x,
        cy,
        c.radius
      );
      coinGrad.addColorStop(0, '#fffbeb');
      coinGrad.addColorStop(0.3, '#fde047');
      coinGrad.addColorStop(0.7, '#f59e0b');
      coinGrad.addColorStop(1, '#78350f');
      this.ctx.fillStyle = coinGrad;
      this.ctx.beginPath();
      this.ctx.arc(c.x, cy, c.radius, 0, Math.PI * 2);
      this.ctx.fill();

      // Specular gleam
      this.ctx.fillStyle = 'rgba(255, 255, 255, 0.85)';
      this.ctx.beginPath();
      this.ctx.arc(c.x - c.radius * 0.35, cy - c.radius * 0.35, c.radius * 0.3, 0, Math.PI * 2);
      this.ctx.fill();
    });

    // Player Ground Drop Shadow (3D depth)
    const shadowScale = Math.max(0.3, 1 - ((this.groundY - (this.playerY + this.character.height)) / 120));
    this.ctx.fillStyle = `rgba(0, 0, 0, ${0.45 * shadowScale})`;
    this.ctx.beginPath();
    this.ctx.ellipse(
      this.playerX + this.character.width / 2,
      this.groundY + 3,
      (this.character.width * 0.5) * shadowScale,
      4 * shadowScale,
      0,
      0,
      Math.PI * 2
    );
    this.ctx.fill();

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
